from django import forms
from dal import autocomplete
from . import models
from accounts.models import Level, Group, Institution


select2_widget = autocomplete.ModelSelect2Multiple(attrs={'data-width': '100%'})

class TargetChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        if type(obj) is Institution:
            count = obj.get_total_users()
            return "{} ({})".format(obj.name, count)
        elif type(obj) is Group:
            count = obj.profile_set.count()
            if obj.institution:
                return f"{obj.institution.name}: {obj.name} ({count})"
            else:
                return f"{obj.name} ({count})"
        elif type(obj) is Level:
            return str(obj)

class MessageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['levels'] = TargetChoiceField(required=False,
                                                   queryset=Level.objects.all(),
                                                   widget=select2_widget)
        self.fields['groups'] = TargetChoiceField(required=False,
                                                   queryset=Group.objects.all(),
                                                   widget=select2_widget)
        self.fields['institutions'] = TargetChoiceField(required=False,
                                                        queryset=Institution.objects.all(),
                                                        widget=select2_widget)

    def clean(self):
        cleaned_data = super().clean()

        if not 'target_type' in cleaned_data:
            return cleaned_data

        if cleaned_data['target_type'] == 'COLLEGES' and \
           (not 'groups' in cleaned_data or not cleaned_data['groups'].exists()):
            raise forms.ValidationError("You did not choose any groups.")

        if cleaned_data['target_type'] == 'INSTITUTIONS' and \
           (not 'institutions' in cleaned_data or not cleaned_data['institutions'].exists()):
            raise forms.ValidationError("You did not choose any institutions.")

        return cleaned_data

    class Meta:
        model = models.Message
        fields = ['from_address', 'subject', 'body', 'target',
                  'institutions', 'groups', 'levels']
        widgets = {'from_address': autocomplete.Select2()}

class MessageTestForm(forms.ModelForm):
    class Meta:
        model = models.Message
        fields = ['from_address', 'subject', 'body']
