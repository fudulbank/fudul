from django import forms
from dal import autocomplete
from django.forms.models import inlineformset_factory
from accounts.utils import get_user_college
from . import models
from teams import utils

class QuestionForm(forms.ModelForm):
    class Meta:
        model = models.Question
        fields = ['sources', 'subjects','exam_type',
                  'status']
        widgets = {
            'sources': autocomplete.ModelSelect2Multiple(url='exams:source_autocomplete',
                                                        forward=['exam_pk']),
            'subjects': autocomplete.ModelSelect2Multiple(url='exams:subject_autocomplete',
                                                         forward=['exam_pk'])
        }

class RevisionForm(forms.ModelForm):

    class Meta:
        model = models.Revision
        fields = ['text', 'explanation', 'figure', 'is_approved','status']

class ChoiceForms(forms.ModelForm):
    class Meta:
        model = models.Choice
        fields = ['text','revision','is_answer']

RevisionChoiceFormset = inlineformset_factory(models.Revision,
                                              models.Choice,
                                              extra=4,
                                              fields=['text','is_answer'])
