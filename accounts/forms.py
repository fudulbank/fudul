from django import forms
from accounts.models import Profile
from userena.forms import SignupFormOnlyEmail, EditProfileForm
from .models import Profile


class CustomSignupForm(SignupFormOnlyEmail):
    first_name = forms.CharField(max_length=30)
    middle_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    alternative_email = forms.EmailField()
    mobile_number = forms.CharField(max_length=15)

    def clean(self, *args, **kwargs):
        cleaned_data = super(CustomSignupForm, self).clean(*args, **kwargs)
        if 'email' in cleaned_data:
            cleaned_data['email'] = cleaned_data['email'].lower()
            if not cleaned_data['email'].endswith('ksau-hs.edu.sa'):
                email_msg = "Please enter a university address"
                self._errors['email'] = self.error_class([email_msg])
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
        user_profile.mobile_number = self.cleaned_data['mobile_number']

        user_profile.save()

        # Userena expects to get the new user from this form, so
        # return the new user.
        return new_user

class CustomEditProfileForm(EditProfileForm):
    password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = Profile
        fields = ['first_name', 'middle_name', 'last_name',
                  'alternative_email', 'mobile_number']
