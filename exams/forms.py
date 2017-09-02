from dal import autocomplete
from django import forms
from django.core.validators import MaxValueValidator,MinValueValidator
from django.forms.models import inlineformset_factory
from accounts.utils import get_user_college
from . import models, utils
import teams.utils


class QuestionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        exam = self.instance.exam

        # Only include 'subjects' field if the exam has subjects
        subjects = models.Subject.objects.filter(exam=exam)
        if subjects.exists():
            self.fields['subjects'].queryset = models.Subject.objects.filter(exam=exam)
            self.fields['subjects'].required = True
        else:
            del self.fields['subjects']

        # Limit sources and exam_types
        self.fields['sources'].queryset = exam.get_sources()

        if exam.exam_types.exists():
            self.fields['exam_types'].queryset = exam.exam_types.all()
            self.fields['exam_types'].required = True
        else:
            del self.fields['exam_types']

    class Meta:
        model = models.Question
        fields = ['sources', 'subjects','exam_types', 'parent_question']
        widgets = {
            'exam_types': autocomplete.ModelSelect2Multiple(attrs={'data-width': '100%'}),
            'parent_question': autocomplete.ModelSelect2(url='exams:autocomplete_questions',
                                                         forward=['exam_pk'],
                                                         attrs={'data-html': True,
                                                                'data-width': '100%'}),
            'sources': autocomplete.ModelSelect2Multiple(attrs={'data-width': '100%'}),
            'subjects': autocomplete.ModelSelect2Multiple(attrs={'data-width': '100%'})
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

        # Limit subjects and exams per exam
        subjects = models.Subject.objects.filter(exam=exam)\
                                         .with_approved_questions()
        if subjects.exists():
            self.fields['subjects'].queryset = subjects              
        else:
            del self.fields['subjects']

        sources = exam.get_sources().filter(parent_source__isnull=True)\
                                    .with_approved_questions()
        if sources.exists():
            self.fields['sources'].queryset = sources
        else:
            del self.fields['sources']

        if exam.exam_types.exists():
            self.fields['exam_types'].queryset = exam.exam_types.with_approved_questions()
            self.fields['exam_types'].required = True
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
            question_pool = question_pool.exclude(answer__session__submitter=session.submitter)
        elif session.question_filter == 'INCORRECT':
            pks = models.Answer.objects.filter(session__exam=session.exam,
                                               session__submitter=session.submitter,
                                               choice__is_right=False)\
                                       .distinct()\
                                       .values_list('question__pk')
            question_pool = question_pool.filter(pk__in=pks)
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
        fields = ['session_mode', 'number_of_questions','exam_types', 'sources','subjects','question_filter']
        widgets = {
            'exam_types': autocomplete.ModelSelect2Multiple(url='exams:exam_type_questions_count',
                                                         forward=['exam_pk'],
                                                         attrs={'data-html': True}),
            'sources': autocomplete.ModelSelect2Multiple(),
            'subjects': autocomplete.ModelSelect2Multiple(url='exams:subject_questions_count',
                                                         forward=['exam_pk'],
                                                         attrs={'data-html': True}),
            # 'subjects': autocomplete.ModelSelect2Multiple(),
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



# class DisabledRevisionForm(RevisionForm):
#     def __init__(self, *args, **kwargs):
#         # Fields to keep enabled.
#         self.enabled_fields = ['statuses']
#         # If an instance is passed, then store it in the instance variable.
#         # This will be used to disable the fields.
#         self.instance = kwargs.get('instance', None)
#
#         # Initialize the form
#         super(DisabledRevisionForm, self).__init__(*args, **kwargs)
#
#         # Make sure that an instance is passed (i.e. the form is being
#         # edited).
#         if self.instance:
#             for field in self.fields:
#                 if not field in self.enabled_fields:
#                     self.fields[field].widget.attrs['readonly'] = 'readonly'
#
#     def clean(self):
#         cleaned_data = super(DisabledRevisionForm, self).clean()
#         if self.instance:
#             for field in cleaned_data:
#                 if not field in self.enabled_fields:
#                     cleaned_data[field] = getattr(self.instance, field)
#
#         return cleaned_data
