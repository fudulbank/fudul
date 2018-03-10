from dal import autocomplete
from django import forms
from django.contrib.auth.models import User

from . import models
from core.forms import MultipleUserChoiceField


class TeamForm(forms.ModelForm):
    members = MultipleUserChoiceField(required=False,
                                      widget=autocomplete.ModelSelect2Multiple(url='user_autocomplete', attrs={'data-html': 'true'}),
                                      queryset=User.objects.order_by('profile__first_name',
                                                                     'profile__middle_name',
                                                                     'profile__last_name'))

    class Meta:
        model = models.Team
        fields = ('__all__')
