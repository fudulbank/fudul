from dal import autocomplete
from django import forms
from . import models

class TeamForm(forms.ModelForm):
    class Meta:
        model = models.Team
        fields = ('__all__')
        widgets = {
            'members': autocomplete.ModelSelect2Multiple(url='user_autocomplete', attrs={'data-html': 'true'})
        }
