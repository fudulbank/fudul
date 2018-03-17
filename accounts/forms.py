from django import forms
from accounts.models import Profile
from userena.forms import SignupFormOnlyEmail, EditProfileForm, identification_field_factory
from . import models
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from userena.models import UserenaSignup
from django.utils.translation import ugettext_lazy as _
from userena import settings as userena_settings
from django.contrib.auth import authenticate

attrs_dict = {'class': 'required'}


class CustomSignupForm(SignupFormOnlyEmail):
    first_name = forms.CharField(max_length=30)
    middle_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    nickname = forms.CharField(max_length=30,required=False)
    alternative_email = forms.EmailField(required=False)
    institution = forms.CharField(max_length=100)
    college = forms.ModelChoiceField(queryset=models.College.objects.all(),
                                     required=False)
    batch = forms.ModelChoiceField(queryset=models.Batch.objects.all(),
                                   required=False)
    mobile_number = forms.CharField(max_length=14)
    primary_interest = forms.ModelChoiceField(queryset=models.PrimaryInterest.objects.filter(children__isnull=True))
    display_full_name = forms.ChoiceField(choices=models.display_full_name_choices)

    def clean(self, *args, **kwargs):
        cleaned_data = super(CustomSignupForm, self).clean(*args, **kwargs)

        if 'alternative_email' in cleaned_data:
            alternative_email = self.cleaned_data['alternative_email']
            if alternative_email and User.objects.filter(profile__alternative_email=alternative_email).exists():
                msg = " Personal email address already registered. "
                self._errors['alternative_email'] = self.error_class([msg])
                del cleaned_data['alternative_email']

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
        user_profile.nickname = self.cleaned_data.get('nickname', None)
        user_profile.mobile_number = self.cleaned_data['mobile_number']
        user_profile.institution = self.cleaned_data['institution']
        user_profile.college = self.cleaned_data.get('college', None)
        user_profile.batch = self.cleaned_data.get('batch', None)
        user_profile.display_full_name = self.cleaned_data['display_full_name']
        user_profile.primary_interest = self.cleaned_data['primary_interest']
        user_profile.personal_email_unconfirmed = self.cleaned_data['alternative_email']

        user_profile.save()
        Profile.objects.generate_key_personal_email(new_user)
        # Userena expects to get the new user from this form, so
        # return the new user.
        return new_user


class CustomEditProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='First name',
                                 max_length=30,
                                 required=False)
    last_name = forms.CharField(label='Last name',
                                max_length=30,
                                required=False)
    display_full_name = forms.ChoiceField(choices=models.display_full_name_choices)
    # nickname = forms.CharField(max_length=30,required=False)
    # institution = forms.CharField(max_length=100)
    # college = forms.ModelChoiceField(queryset=models.College.objects.all(),
    #                                  required=False)
    # batch = forms.ModelChoiceField(queryset=models.Batch.objects.all(),
    #                                required=False)


    # def __init__(self, user, *args, **kwargs):
    #     self.user = user
    #     super(CustomEditProfileForm,self).__init__(*args, **kwargs)

    # def __init__(self, *args, **kwargs):
    #     assert 'activity' in kwargs, "Kwarg 'activity' is required."
    #     assert 'user' in kwargs, "Kwarg 'user' is required."
    #     self.activity = kwargs.pop("activity", None)
    #     self.user = kwargs.pop("user", None)
    #
    class Meta:
        model = models.Profile
        fields = ['first_name', 'middle_name', 'last_name',
                  'nickname', 'mobile_number','display_full_name']

    def clean(self):
        cleaned_data = super(CustomEditProfileForm, self).clean()

        # if 'institution' in cleaned_data:
        #     institution_name = cleaned_data['institution']
        #     try:
        #         institution = models.Institution.objects.get(name=institution_name)
        #     except models.Institution.DoesNotExist:
        #         # The user has manually entered an institution name.
        #         # This will be handled by built-in form validation.
        #         pass
        #     else:
        #         if institution.college_set.exists() and \
        #            (not 'college' in cleaned_data or not cleaned_data['college']):
        #             raise forms.ValidationError("You did not choose a college within {}.".format(institution.name))
        #         elif institution.college_set.exists():
        #             # College check
        #             college = cleaned_data['college']
        #             # Make sure that the selected colleges falls under the institution
        #             if not institution.college_set.filter(pk=college.pk).exists():
        #                 msg = ("The college you entered is not part of "
        #                        "{}.".format(institution.name))
        #                 self._errors['college'] = self.error_class([msg])
        #                 del cleaned_data['college']
        # # Email check
        # if 'email' in cleaned_data:
        #     email = cleaned_data['email']
        #     if not institution.is_email_allowed(email):
        #         msg = ("The email you entered does not allow you to sign "
        #                "up for {}.".format(institution_name))
        #         self._errors['email'] = self.error_class([msg])
        #         del cleaned_data['email']

        return cleaned_data

    def save(self):
        user_profile = super(CustomEditProfileForm, self).save()

        # user_profile.institution = self.cleaned_data['institution']
        # user_profile.college = self.cleaned_data.get('college', None)
        # user_profile.batch = self.cleaned_data.get('batch', None)

        # if user_profile.alternative_email:
        #     alternative_email = user_profile.alternative_email
        #     user = user_profile.user
        #     if alternative_email and User.objects.filter(profile__alternative_email=alternative_email).exclude(profile__user=user).exists():
        #         raise ValidationError("Personal email is already registered")

        user_profile.save()



class ChangePersonalEmailForm(forms.Form):
    alternative_email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict,maxlength=75)),label="New personal email")

    def __init__(self, user, *args, **kwargs):
        """
        The current ``user`` is needed for initialisation of this form so
        that we can check if the email address is still free and not always
        returning ``True`` for this query because it's the users own e-mail
        address.

        """
        super(ChangePersonalEmailForm, self).__init__(*args, **kwargs)
        if not isinstance(user, User):
            raise TypeError("user must be an instance of %s" % User)
        else: self.user = user



    def clean(self):

        cleaned_data = super(ChangePersonalEmailForm, self).clean()

        if 'alternative_email' in cleaned_data:
            alternative_email = self.cleaned_data['alternative_email']
            if alternative_email and User.objects.filter(profile__alternative_email=alternative_email).exclude(
                    profile__alternative_email__iexact=self.user.profile.alternative_email):
                msg = " Personal email address already registered. "
                self._errors['alternative_email'] = self.error_class([msg])
                del cleaned_data['alternative_email']
            elif cleaned_data['alternative_email'].lower() == self.user.profile.alternative_email.lower():
                msg = " You\'re already known under this email. "
                self._errors['alternative_email'] = self.error_class([msg])
                del cleaned_data['alternative_email']


    def save(self):
        """
        Save method calls :func:`user.change_email()` method which sends out an
        email with an verification key to verify and with it enable this new
        email address.

        """

        return self.user.profile.change_personal_email(self.cleaned_data['alternative_email'])


class CustomAuthenticationForm(forms.Form):
    identification =identification_field_factory(_("Main or alternative email"),
                                                  _("Either supply us with your main or alternative email."))

    password = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput(attrs=attrs_dict, render_value=False))
    remember_me = forms.BooleanField(widget=forms.CheckboxInput(),
                                     required=False,
                                     label=_('Remember me for %(days)s') % {'days': _(userena_settings.USERENA_REMEMBER_ME_DAYS[0])})

    def __init__(self, *args, **kwargs):
        """ A custom init because we need to change the label if no usernames is used """
        super(CustomAuthenticationForm, self).__init__(*args, **kwargs)
        # Dirty hack, somehow the label doesn't get translated without declaring
        # it again here.
        self.fields['remember_me'].label = _('Remember me for %(days)s') % {'days': _(userena_settings.USERENA_REMEMBER_ME_DAYS[0])}
        if userena_settings.USERENA_WITHOUT_USERNAMES:
            self.fields['identification'] = identification_field_factory(_("Email"),
                                                                         _("Please supply your email."))

    def clean(self):
        """
        Checks for the identification and password.

        If the combination can't be found will raise an invalid sign in error.

        """
        identification = self.cleaned_data.get('identification')
        password = self.cleaned_data.get('password')

        if identification and password:
            user = authenticate(identification=identification, password=password)
            if user is None:
                raise forms.ValidationError(_("Please enter a correct username or email and password. Note that both fields are case-sensitive."))
        return self.cleaned_data
