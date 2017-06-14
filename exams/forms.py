from django import forms
from dal import autocomplete
from django.forms.models import inlineformset_factory
from accounts.utils import get_user_college
from . import models
from teams import utils

class QuestionForm(forms.ModelForm):
    class Meta:
        model = models.Question
        fields = ['sources', 'subjects', 'figure', 'exam_type',
                  'status']
        widgets = {
            'sources': autocomplete.ModelSelect2Multiple(url='exams:source_autocomplete',
                                                        forward=['exam_pk']),
            'subjects': autocomplete.ModelSelect2Multiple(url='exams:subject_autocomplete',
                                                         forward=['exam_pk'])
        }

class RevisionForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        # Remove is_publicly_owned field from ordinary users.
        assert 'user' in kwargs, "Kwarg 'user' is required."
        super(RevisionForm, self).__init__(*args, **kwargs)
        if self.question.get_ultimate_latest_revision() is not None:
            self.fields['text'] = self.question.get_ultimate_latest_revision().text


    def save(self, *args, **kwargs):
        if utils.is_editor(self.user):
            self.is_approved = True
            return super(RevisionForm, self).save(*args, **kwargs)

    class Meta:
        model = models.Revision
        fields = ['text', 'explanation']

class ChoiceForms(forms.ModelForm):
    class Meta:
        model = models.Choice
        fields = ['text','revision','is_answer']

RevisionChoiceFormset = inlineformset_factory(models.Revision,
                                              models.Choice,
                                              extra=4,
                                              fields=['text','is_answer'])
