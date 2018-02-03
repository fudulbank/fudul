from django import forms
from dal import autocomplete
from . import models
from accounts.models import Batch, College, Institution


select2_widget = autocomplete.ModelSelect2Multiple(attrs={'data-width': '100%'})

class TargetChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        if type(obj) is Institution:
            count = obj.get_total_users()
            return "{} ({})".format(obj.name, count)
        elif type(obj) is College:
            count = obj.profile_set.count()
            return "{}: {} ({})".format(obj.institution.name, obj.name, count)
        elif type(obj) is Batch:
            return str(obj)

class MessageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(MessageForm, self).__init__(*args, **kwargs)
        self.fields['batches'] = TargetChoiceField(required=False,
                                                   queryset=Batch.objects.all(),
                                                   widget=select2_widget)
        self.fields['colleges'] = TargetChoiceField(required=False,
                                                   queryset=College.objects.all(),
                                                   widget=select2_widget)
        self.fields['institutions'] = TargetChoiceField(required=False,
                                                        queryset=Institution.objects.all(),
                                                        widget=select2_widget)

    def clean(self):
        cleaned_data = super(MessageForm, self).clean()

        if not 'target_type' in cleaned_data:
            return cleaned_data

        if cleaned_data['target_type'] == 'COLLEGES' and \
           (not 'colleges' in cleaned_data or not cleaned_data['colleges'].exists()):
            raise forms.ValidationError("You did not choose any colleges.")
        
        if cleaned_data['target_type'] == 'INSTITUTIONS' and \
           (not 'institutions' in cleaned_data or not cleaned_data['institutions'].exists()):
            raise forms.ValidationError("You did not choose any institutions.")

        return cleaned_data

    class Meta:
        model = models.Message
        fields = ['from_address', 'subject', 'body', 'target',
                  'institutions', 'colleges', 'batches']
        widgets = {'from_address': autocomplete.Select2()}

class MessageTestForm(forms.ModelForm):
    class Meta:
        model = models.Message
        fields = ['from_address', 'subject', 'body']
