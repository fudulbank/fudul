from django import forms
from blocks.models import Exam,Question,Revision,Choice


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['name']


class QuestionForm(forms.ModelForm):

    class Meta:
        model = Question
        fields = ['source','subject','figure','exam_type']


class RevisionForms(forms.ModelForm):

    class Meta:
        model =Revision
        fields = ['text','explanation',]


class ChoiceForms(forms.ModelForm):

    class Meta:
        model = Choice
        fields = ['text','revision','is_answer']




