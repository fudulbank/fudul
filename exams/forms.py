from dal import autocomplete
from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
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

class StatusChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        if obj.is_blocker:
            blocker_str = "blocker"
            css_class = "text-danger"
        else:
            blocker_str = "nonblocker"
            css_class = "text-success"
        return "{} <strong class='{}'>({})</strong>".format(obj.name, css_class, blocker_str)

# shared widgets for exam_types, sources and subjects in QuestionForm and SessionForm
select2_widget = autocomplete.ModelSelect2Multiple(attrs={'data-width': '100%'})
    
class QuestionForm(forms.ModelForm):
    issues = StatusChoiceField(widget=autocomplete.ModelSelect2Multiple(attrs={'data-width': '100%', 'data-html': 'true'}),
                               queryset=models.Issue.objects.all(),
                               required=False)

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
        fields = ['sources', 'subjects', 'exam_types',
                  'parent_question', 'issues']
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
        new_revision.is_contribution = not teams.utils.is_editor(user)
        new_revision.save()
        self.save_m2m()

        # Make sure that all previous revisions are set to
        # is_last=False
        question.revision_set.exclude(pk=new_revision.pk)\
                             .update(is_last=False)

        return new_revision

    class Meta:
        model = models.Revision
        fields = ['text', 'explanation', 'explanation_figure',
                  'figure', 'is_approved','reference',
                  'change_summary','is_contribution']


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
                                              extra=1,
                                              fields=['text','is_right'])

class SessionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.exam = kwargs.pop('exam')
        self.user = kwargs.pop('user')
        super(SessionForm, self).__init__(*args, **kwargs)

        self.fields['session_mode'].widget = forms.RadioSelect(choices=models.session_mode_choices[:-1])

        self.question_pools = {'ALL': self.exam.question_set.approved(),
                               'UNUSED': self.exam.question_set.approved().unused_by_user(self.user),
                               'INCORRECT': self.exam.question_set.approved().incorrect_by_user(self.user),
                               'MARKED': self.exam.question_set.approved().filter(marking_users=self.user),
                               'INCOMPLETE': self.exam.question_set.with_blocking_issues() |\
                                             self.exam.question_set.unsolved() |\
                                             self.exam.question_set.lacking_choices()
                               }

        filter_choices = []
        for code_name, human_name in models.questions_choices:
            question_pool = self.question_pools[code_name]
            count = question_pool.count()
            choice = (code_name, "{} ({})".format(human_name, count))
            filter_choices.append(choice)
        self.fields['question_filter'].widget = forms.RadioSelect(choices=filter_choices)

        # Limit number of questions
        total_questions = self.exam.question_set.approved().count()
        self.fields['number_of_questions'].widget.attrs['max'] = total_questions

        self.fields['number_of_questions'].validators.append(MinValueValidator(1))
        self.fields['number_of_questions'].widget.attrs['min'] = 1
        # This widget should be big enough to contain 5 digits.
        self.fields['number_of_questions'].widget.attrs['style'] = 'width: 5em;'
        self.fields['number_of_questions'].widget.attrs['placeholder'] = ''

        # Limit subjects and exams per exam
        subjects = models.Subject.objects.filter(exam=self.exam)\
                                         .with_approved_questions()\
                                         .distinct()
        if subjects.exists():
            self.fields['subjects'] = MetaChoiceField(exam=self.exam,
                                                      required=False,
                                                      form_type='session',
                                                      queryset=subjects,
                                                      widget=select2_widget)
        else:
            del self.fields['subjects']

        sources = self.exam.get_sources().filter(parent_source__isnull=True)\
                                         .with_approved_questions(self.exam)\
                                         .distinct()
        if sources.exists():
            self.fields['sources'] = MetaChoiceField(exam=self.exam,
                                                     required=False,
                                                     form_type='session',
                                                     queryset=sources,
                                                     widget=select2_widget)
        else:
            del self.fields['sources']

        exam_types = self.exam.exam_types.with_approved_questions(self.exam)\
                                         .distinct()
        if exam_types.exists():
            self.fields['exam_types'] = MetaChoiceField(required=True,
                                                        form_type='session',
                                                        exam=self.exam,
                                                        queryset=exam_types,
                                                        widget=select2_widget)
        else:
            del self.fields['exam_types']

    def clean(self):
        cleaned_data = super(SessionForm, self).clean()

        # If the form is invalid to start with, skip question
        # checking.

        if not 'question_filter' in cleaned_data or \
           not 'number_of_questions' in cleaned_data:
            return cleaned_data

        question_filter = cleaned_data['question_filter']
        question_pool = self.question_pools[question_filter]

        subjects = cleaned_data.get('subjects')
        if subjects:
            question_pool = question_pool.filter(subjects__in=subjects)

        sources = cleaned_data.get('sources')
        if sources:
            question_pool = question_pool.filter(sources__in=sources)

        exam_types = cleaned_data.get('exam_types')
        if exam_types:
            question_pool = question_pool.filter(exam_types__in=exam_types)

        if not question_pool.exists():
            raise forms.ValidationError("No questions at all match your selection.  Please try other options.")
    
        # Let's make sure that when a question is randomly chosen, we
        # also include its parents and children.
        selected_pks = []
        for question in question_pool.iterator():
            tree = question.get_tree()
            new_pks = [q.pk for q in tree if not q.pk in selected_pks]
            selected_pks += new_pks

            # Check unique questions
            selected_questions = models.Question.objects.select_related('parent_question')\
                                                        .filter(pk__in=selected_pks)
            if question_filter != 'INCOMPLETE':
                selected_questions = selected_questions.approved()
            if selected_questions.count() >= cleaned_data['number_of_questions']:
                break

        self.questions = selected_questions

        return cleaned_data

    def save(self, *args, **kwargs):
        session = super(SessionForm, self).save(*args, **kwargs)
        session.questions.add(*self.questions)
        return session

    class Meta:
        model = models.Session
        fields = ['session_mode', 'number_of_questions','exam_types',
                  'sources', 'subjects', 'question_filter']


class ExplanationForm(RevisionForm):
    def __init__(self, *args, **kwargs):
        super(ExplanationForm, self).__init__(*args, **kwargs)
        self.fields['explanation'].required = True


    class Meta:
        model = models.Revision
        fields = ['explanation', 'explanation_figure', 'reference']


class AnswerCorrectionForm(forms.ModelForm):
    class Meta:
        model = models.AnswerCorrection
        fields = ['justification']

