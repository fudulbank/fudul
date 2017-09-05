from dal import autocomplete
from django import forms
from django.core.validators import MaxValueValidator,MinValueValidator
from django.forms.models import inlineformset_factory
from accounts.utils import get_user_college
from . import models, utils
import teams.utils

class MetaChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        self.exam = kwargs.pop('exam')
        self.form_type = kwargs.pop('form_type')
        super(MetaChoiceField, self).__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        approved_only = self.form_type == 'session'
        count = utils.get_exam_question_count_per_meta(self.exam,
                                                       meta=obj,
                                                       approved_only=approved_only)

        return "{} ({})".format(str(obj), count)

# shared widgets for exam_types, sources and subjects in QuestionForm and SessionForm
select2_widget = autocomplete.ModelSelect2Multiple(attrs={'data-width': '100%'})
    
class QuestionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        exam = self.instance.exam

        # Only include 'subjects' field if the exam has subjects
        subjects = models.Subject.objects.filter(exam=exam)
        if subjects.exists():
            self.fields['subjects'] = MetaChoiceField(required=True,
                                                      form_type='question',
                                                      exam=exam,
                                                      queryset=subjects,
                                                      widget=select2_widget)
        else:
            del self.fields['subjects']

        sources = exam.get_sources()
        if sources.exists():
            self.fields['sources'] = MetaChoiceField(required=True,
                                                     form_type='question',
                                                     exam=exam,
                                                     queryset=sources,
                                                     widget=select2_widget)
        else:
            del self.fields['sources']

        if exam.exam_types.exists():
            self.fields['exam_types'] = MetaChoiceField(required=True,
                                                        form_type='question',
                                                        exam=exam,
                                                        queryset=exam.exam_types.all(),
                                                        widget=select2_widget)
        else:
            del self.fields['exam_types']

    class Meta:
        model = models.Question
        fields = ['sources', 'subjects','exam_types', 'parent_question']
        widgets = {
            'parent_question': autocomplete.ModelSelect2(url='exams:autocomplete_questions',
                                                         forward=['exam_pk'],
                                                         attrs={'data-html': True,
                                                                'data-width': '100%'}),
        }

class RevisionForm(forms.ModelForm):
    def clone(self, question, user):
        new_revision = self.save(commit=False)

        # Setting primary key to None creates a new object, rather
        # than modifying the pre-existing one
        new_revision.pk = None
        new_revision.submitter = user
        new_revision.save()
        self.save_m2m()

        # Make sure that all previous revisions are set to
        # is_last=False
        question.revision_set.exclude(pk=new_revision.pk)\
                             .update(is_last=False)

        new_revision.is_approved = utils.test_revision_approval(new_revision)

        if teams.utils.is_editor(user):
            new_revision.is_contribution = False
        else:
            new_revision.is_contribution = True

        new_revision.save()

        return new_revision

    class Meta:
        model = models.Revision
        fields = ['text', 'explanation', 'explanation_figure',
                  'figure', 'is_approved', 'statuses','reference',
                  'change_summary','is_contribution']
        widgets = {
            'statuses': autocomplete.ModelSelect2Multiple(attrs={'data-width': '100%'}),
        }

class ChoiceForms(forms.ModelForm):
    class Meta:
        model = models.Choice
        fields = ['text','revision','is_right']

class CustomRevisionChoiceFormset(forms.BaseInlineFormSet):
    def clone(self, revision):
        # Let's clone choices!
        modified_choices = self.save(commit=False)
        unmodified_choices = []
        for choice in self.queryset:
            if not choice in self.deleted_objects and \
               not choice in modified_choices:
                unmodified_choices.append(choice)
        choices = modified_choices + unmodified_choices
        for choice in choices:
            choice.pk = None
            choice.revision = revision
            choice.save()

RevisionChoiceFormset = inlineformset_factory(models.Revision,
                                              models.Choice,
                                              formset=CustomRevisionChoiceFormset,
                                              extra=4,
                                              fields=['text','is_right'])


ContributedRevisionChoiceFormset = inlineformset_factory(models.Revision,
                                              models.Choice,
                                              formset=CustomRevisionChoiceFormset,
                                              extra=0,
                                              fields=['text','is_right'])

class SessionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        exam = kwargs.pop('exam')
        super(SessionForm, self).__init__(*args, **kwargs)

        # Limit number of questions
        total_questions = exam.question_set.approved().count()
        total_question_validator = MaxValueValidator(total_questions)
        self.fields['number_of_questions'].validators.append(total_question_validator)
        self.fields['number_of_questions'].widget.attrs['max'] = total_questions

        self.fields['number_of_questions'].validators.append(MinValueValidator(1))
        self.fields['number_of_questions'].widget.attrs['min'] = 1
        # This widget should be big enough to contain 5 digits.
        self.fields['number_of_questions'].widget.attrs['style'] = 'width: 5em;'
        self.fields['number_of_questions'].widget.attrs['placeholder'] = ''

        # Limit subjects and exams per exam
        subjects = models.Subject.objects.filter(exam=exam)\
                                         .with_approved_questions()\
                                         .distinct()
        if subjects.exists():
            self.fields['subjects'] = MetaChoiceField(exam=exam,
                                                      form_type='session',
                                                      queryset=subjects,
                                                      widget=select2_widget)
        else:
            del self.fields['subjects']

        sources = exam.get_sources().filter(parent_source__isnull=True)\
                                    .with_approved_questions(exam)\
                                    .distinct()
        if sources.exists():
            self.fields['sources'] = MetaChoiceField(exam=exam,
                                                     form_type='session',
                                                     queryset=sources,
                                                     widget=select2_widget)
        else:
            del self.fields['sources']

        exam_types = exam.exam_types.with_approved_questions(exam)\
                                    .distinct()
        if exam_types.exists():
            self.fields['exam_types'] = MetaChoiceField(required=True,
                                                        form_type='session',
                                                        exam=exam,
                                                        queryset=exam_types,
                                                        widget=select2_widget)
        else:
            del self.fields['exam_types']

    def save(self, *args, **kwargs):
        session = super(SessionForm, self).save(*args, **kwargs)
        question_pool = session.exam.question_set.approved()\
                                    .order_by('?')\
                                    .select_related('parent_question',
                                                    'child_question')

        if session.subjects.exists():
            question_pool = question_pool.filter(subjects__in=session.subjects.all())

        if session.sources.exists():
            question_pool = question_pool.filter(sources__in=session.sources.all())

        if session.exam_types.exists():
            question_pool = question_pool.filter(exam_types__in=session.exam_types.all())

        if session.question_filter == 'UNUSED':
            question_pool = question_pool.unused_by_user(session.submitter)
        elif session.question_filter == 'INCORRECT':
            question_pool = question_pool.incorrect_by_user(session.submitter)
        elif session.question_filter == 'MARKED':
            question_pool = question_pool.filter(marking_users=session.submitter)

        # Let's make sure that when a question is randomly chosen, we
        # also include its parents and children.
        selected = []
        for question in question_pool.iterator():
            tree = question.get_tree()
            selected += tree

            if len(selected) >= session.number_of_questions:
                break

        # In the course of ensuring inclusion of the complete question
        # child/parent tree, we might have exceeded the required
        # number.  So let's cut on that.
        final = selected
        if len(selected) > session.number_of_questions:
            for question in selected:
                if not hasattr(question, 'child_question') and \
                   not question.parent_question:
                    final.remove(question)

        session.questions.add(*final)

        return session

    class Meta:
        model = models.Session
        fields = ['session_mode', 'number_of_questions','exam_types',
                  'sources', 'subjects', 'question_filter']
        widgets = {
            'question_filter':forms.RadioSelect(choices=models.questions_choices),
            'session_mode':forms.RadioSelect(choices=models.session_mode_choices)
            }


class ExplanationForm(RevisionForm):
    def __init__(self, *args, **kwargs):
        super(ExplanationForm, self).__init__(*args, **kwargs)
        self.fields['explanation'].required = True

    class Meta:
        model = models.Revision
        fields = ['explanation', 'explanation_figure']

