from dal import autocomplete
from django import forms
from django.contrib.auth.models import User

from . import models
from core.forms import MultipleUserChoiceField


class TeamForm(forms.ModelForm):
    memers = MultipleUserChoiceField(required=False,
                                     queryset=User.objects.all())

    class Meta:
        model = models.Team
        fields = ('__all__')
        widgets = {
            'members': autocomplete.ModelSelect2Multiple(url='user_autocomplete', attrs={'data-html': 'true'})
        }
