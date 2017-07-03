from django import forms
from dal import autocomplete
from django.forms.models import inlineformset_factory
from django.core.validators import MaxValueValidator
from accounts.utils import get_user_college
from . import models
from teams import utils

class QuestionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        exam = kwargs.pop('exam')
        super(QuestionForm, self).__init__(*args, **kwargs)
        self.fields['subjects'].queryset = models.Subject.objects.filter(exam=exam)
        self.fields['sources'].queryset = exam.get_sources()

    class Meta:
        model = models.Question
        fields = ['sources', 'subjects','exam_type', 'parent_question']
        widgets = {
            'exam_type': autocomplete.ListSelect2(),
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
        self.fields['sources'].queryset = exam.get_sources()

    class Meta:
        model = models.Session
        fields = ['explained','number_of_questions','session_type','solved','sources','subjects']
        widgets = {
            'sources': autocomplete.ModelSelect2Multiple(),
            'subjects': autocomplete.ModelSelect2Multiple(),
            }
