from django import forms
from blocks.models import Exam,Question,Revision,Choice,Subject,Source
from accounts.utils import get_user_college
from django.forms.models import inlineformset_factory


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['name']


class QuestionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        assert 'user' in kwargs, "Kwarg 'user' is required."
        self.user = kwargs.pop("user", None)
        exam = kwargs.get('exam', None)
        super(QuestionForm, self).__init__(*args, **kwargs)
        subject = Subject.objects.filter(exam=exam)
        self.fields['subject'].queryset = subject
        self.subject = None
        college = get_user_college(self.user)
        self.fields['source'].queryset = Source.objects.filter(college=college)
        self.source = None

    # def save(self, *args, **kwargs):
    #     question = super(QuestionForm, self).save(commit=False)
    #     if self.source:
    #         question.source =self.source
    #     if self.subject:
    #         question.subject =self.subject
    #     question.save()
    #     return question

    class Meta:
        model = Question
        fields = ['source','subject','figure','exam_type','status']


class RevisionForm(forms.ModelForm):
    class Meta:
        model = Revision
        fields = ['text','explanation',]


class ChoiceForms(forms.ModelForm):

    class Meta:
        model = Choice
        fields = ['text','revision','is_answer']

RevisionChoiceFormset = inlineformset_factory(Revision,
                                              Choice,
                                              fields=['text','is_answer'])


