from django import forms
from accounts.models import Profile
from userena.forms import SignupFormOnlyEmail, EditProfileForm
from . import models


class CustomSignupForm(SignupFormOnlyEmail):
    first_name = forms.CharField(max_length=30)
    middle_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    nickname = forms.CharField(max_length=30)
    alternative_email = forms.EmailField()
    institution = forms.CharField(max_length=100)
    college = forms.ModelChoiceField(queryset=models.College.objects.all(),
                                     required=False)
    batch = forms.ModelChoiceField(queryset=models.Batch.objects.all(),
                                   required=False)    
    mobile_number = forms.CharField(max_length=14)

    def clean(self, *args, **kwargs):
        cleaned_data = super(CustomSignupForm, self).clean(*args, **kwargs)

        if 'institution' in cleaned_data:
            institution_name = cleaned_data['institution']
            try:
                institution = models.Institution.objects.get(name=institution_name)
            except models.Institution.DoesNotExist:
                # The user has manually entered an institution name.
                # This will be handled by built-in form validation.
                pass
            else:
                if institution.college_set.exists() and \
                   (not 'college' in cleaned_data or \
                    not cleaned_data['college']):
                    raise forms.ValidationError("You did not choose a college within {}.".format(institution.name))
                elif institution.college_set.exists():
                    # College check
                    college = cleaned_data['college']
                    # Make sure that the selected colleges falls under the institution
                    if not institution.college_set.filter(pk=college.pk).exists():
                        msg = ("The college you entered is not part of "
                               "{}.".format(institution.name))
                        self._errors['college'] = self.error_class([msg])
                        del cleaned_data['college']

                # Email check
                if 'email' in cleaned_data:
                    email = cleaned_data['email']
                    if not institution.is_email_allowed(email):
                        msg = ("The email you entered does not allow you to sign "
                               "up for {}.".format(institution_name))
                        self._errors['email'] = self.error_class([msg])
                        del cleaned_data['email']

        return cleaned_data

    def save(self):
        """
        Override the save method to save the new fields
        """
        # First save the parent form and get the user.
        new_user = super(CustomSignupForm, self).save()

        # Get the profile, the `save` method above creates a profile for each
        # user because it calls the manager method `create_user`.
        # See: https://github.com/bread-and-pepper/django-userena/blob/master/userena/managers.py#L65
        user_profile = new_user.profile

        user_profile.first_name = self.cleaned_data['first_name']
        user_profile.middle_name = self.cleaned_data['middle_name']
        user_profile.last_name = self.cleaned_data['last_name']
        user_profile.nickname = self.cleaned_data['nickname']
        user_profile.mobile_number = self.cleaned_data['mobile_number']
        user_profile.institution = self.cleaned_data['institution']
        user_profile.college = self.cleaned_data.get('college', None)
        user_profile.batch = self.cleaned_data.get('batch', None)

        user_profile.save()

        # Userena expects to get the new user from this form, so
        # return the new user.
        return new_user


class CustomEditProfileForm(EditProfileForm):
    password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = models.Profile
        fields = ['first_name', 'middle_name', 'last_name',
                  'nickname', 'alternative_email', 'mobile_number']
