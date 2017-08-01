from django import forms
from django.core.exceptions import ObjectDoesNotExist
import accounts.utils

class MultipleUserChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return accounts.utils.get_user_representation(obj)

