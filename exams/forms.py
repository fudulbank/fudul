from dal import autocomplete
from django import forms
from django.core.validators import MaxValueValidator
from django.forms.models import inlineformset_factory
from accounts.utils import get_user_college
from . import models
from teams import utils


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

RevisionChoiceFormset = inlineformset_factory(models.Revision,
                                              models.Choice,
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

        exam_types = exam.get_exam_types()
        if exam_types.exists():
            self.fields['exam_types'].queryset = exam_types
        else:
            del self.fields['exam_types']

    class Meta:
        model = models.Session
        fields = ['number_of_questions','exam_types','solved','sources','subjects','unsloved','incoorect','marked']
        widgets = {
            'exam_types': autocomplete.ModelSelect2Multiple(),
            'sources': autocomplete.ModelSelect2Multiple(),
            'subjects': autocomplete.ModelSelect2Multiple(),
            }
