from django import forms
from blocks.models import Block,Question


class BlockForm(forms.ModelForm):
    class Meta:
        model= Block
        fields=['name']


class QuestionForm(forms.ModelForm):
    
    class Meta:
        model= Question
        fields=['subject','batch','text','explanation','figure','type']

