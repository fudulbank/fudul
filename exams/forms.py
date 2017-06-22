from django import forms
from dal import autocomplete
from django.forms.models import inlineformset_factory
from accounts.utils import get_user_college
from . import models
from teams import utils

class QuestionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        exam = kwargs.pop('exams')
        super(QuestionForm, self).__init__(*args, **kwargs)
        self.fields['subjects'] = models.Subject.objects.filter(exam=exam)
        self.fields['sources'] = exam.get_sources()

    class Meta:
        model = models.Question
        fields = ['sources', 'subjects','exam_type',
                  'statuses']
        widgets = {
            'exam_type': autocomplete.ListSelect2(),
            'statuses': autocomplete.ModelSelect2Multiple(),
            'sources': autocomplete.ModelSelect2Multiple(forward=['exam_pk']),
            'subjects': autocomplete.ModelSelect2Multiple(forward=['exam_pk'])
        }

class RevisionForm(forms.ModelForm):

    class Meta:
        model = models.Revision
        fields = ['text', 'explanation', 'figure', 'is_approved']

class ChoiceForms(forms.ModelForm):
    class Meta:
        model = models.Choice
        fields = ['text','revision','is_answer']

RevisionChoiceFormset = inlineformset_factory(models.Revision,
                                              models.Choice,
                                              extra=4,
                                              fields=['text','is_answer'])
