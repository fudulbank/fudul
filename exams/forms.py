from dal import autocomplete
from django import forms
from django.core.validators import MaxValueValidator
from django.forms.models import inlineformset_factory
from accounts.utils import get_user_college
from . import models, utils
import teams.utils


class QuestionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        exam = kwargs.pop('exam')
        super(QuestionForm, self).__init__(*args, **kwargs)
        self.fields['subjects'].queryset = models.Subject.objects.filter(exam=exam)
        self.fields['sources'].queryset = exam.get_sources()

        exam_types = exam.get_exam_types()
        if exam_types.exists():
            self.fields['exam_types'].queryset = exam_types
        else:
            del self.fields['exam_types']

    class Meta:
        model = models.Question
        fields = ['sources', 'subjects','exam_types', 'parent_question']
        widgets = {
            'exam_types': autocomplete.ModelSelect2Multiple(),
            'parent_question': autocomplete.ModelSelect2(url='exams:autocomplete_questions',
                                                         forward=['exam_pk'],
                                                         attrs={'data-html': True}),
            'sources': autocomplete.ModelSelect2Multiple(),
            'subjects': autocomplete.ModelSelect2Multiple()
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

        if utils.test_revision_approval(new_revision, user):
            new_revision.is_approved = True
        else:
            new_revision.is_approved = False

        new_revision.save()

        return new_revision

    class Meta:
        model = models.Revision
        fields = ['text', 'explanation', 'figure', 'is_approved',
                  'statuses']
        widgets = {
            'statuses': autocomplete.ModelSelect2Multiple(),
        }

class ChoiceForms(forms.ModelForm):
    class Meta:
        model = models.Choice
        fields = ['text','revision','is_answer']

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
                                              fields=['text','is_answer'])

class SessionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        exam = kwargs.pop('exam')
        super(SessionForm, self).__init__(*args, **kwargs)

        # Limit number of questions
        total_questions = exam.get_approved_questions().count()
        total_question_validator = MaxValueValidator(total_questions)
        self.fields['number_of_questions'].validators.append(total_question_validator)
        self.fields['number_of_questions'].widget.attrs['max'] = total_questions

        # Limit subjects and exams per exam
        self.fields['subjects'].queryset = models.Subject.objects.filter(exam=exam)
        self.fields['sources'].queryset = exam.get_sources().filter(parent_source__isnull=True)
        # self.fields['question_filter']=forms.ChoiceField(choices=models.questions_choices)

        exam_types = exam.get_exam_types()
        if exam_types.exists():
            self.fields['exam_types'].queryset = exam_types
        else:
            del self.fields['exam_types']


    class Meta:
        model = models.Session
        fields = ['number_of_questions','exam_types','solved','sources','subjects','question_filter']
        widgets = {
            'exam_types': autocomplete.ModelSelect2Multiple(),
            'sources': autocomplete.ModelSelect2Multiple(),
            'subjects': autocomplete.ModelSelect2Multiple(url='exams:subject_questions_count',
                                                         forward=['exam_pk'],
                                                         attrs={'data-html': True}),
            'question_filter':forms.RadioSelect(choices=models.questions_choices)
            }


class ExplanationForm(RevisionForm):
    def __init__(self, *args, **kwargs):
        super(ExplanationForm, self).__init__(*args, **kwargs)
        self.fields['explanation'].required  = True

    class Meta:
        model = models.Revision
        fields = ['explanation']
