from dal import autocomplete
from django import forms
from django.contrib.auth.models import User

from . import models
from core.forms import MultipleUserChoiceField


class TeamForm(forms.ModelForm):
    members = MultipleUserChoiceField(required=False,
                                      widget=autocomplete.ModelSelect2Multiple(url='user_autocomplete', attrs={'data-html': 'true'}),
                                      queryset=User.objects.all())

    class Meta:
        model = models.Team
        fields = ('__all__')
