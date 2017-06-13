from django import forms
from dal import autocomplete
from django.forms.models import inlineformset_factory
from accounts.utils import get_user_college
from . import models

class QuestionForm(forms.ModelForm):
    class Meta:
        model = models.Question
        fields = ['sources', 'subjects', 'figure', 'exam_type',
                  'status']
        widgets = {
            'sources': autocomplete.ModelSelect2Multiple(url='blocks:source_autocomplete',
                                                        forward=['exam_pk']),
            'subjects': autocomplete.ModelSelect2Multiple(url='blocks:subject_autocomplete',
                                                         forward=['exam_pk'])
        }

class RevisionForm(forms.ModelForm):
    class Meta:
        model = models.Revision
        fields = ['text', 'explanation']

class ChoiceForms(forms.ModelForm):
    class Meta:
        model = models.Choice
        fields = ['text','revision','is_answer']

RevisionChoiceFormset = inlineformset_factory(models.Revision,
                                              models.Choice,
                                              fields=['text','is_answer'])


