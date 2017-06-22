from django import forms
from dal import autocomplete
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

    class Meta:
        model = models.Question
        fields = ['sources', 'subjects','exam_type']
        widgets = {
            'exam_type': autocomplete.ListSelect2(),
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
