from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import models
from django.db.models import Count
from django.utils.translation import ugettext as _
from userena import settings as userena_settings
from userena.mail import UserenaConfirmationMail
from userena.models import UserenaBaseProfile
from userena.utils import generate_sha1,get_datetime_now,get_protocol
import datetime
import re

from . import managers


display_full_name_choices = (
    ('Y', 'Display my full name'),
    ('N', 'Display only nickname'),
)

primary_interest_choices = (
    ('', '------'),
    ('SMLE', 'SMLE'),
    ('SNLE', 'SNLE'),
    ('RESIDENCY', 'Residency exams'),
    ('COLLEGE', 'Colege exams'),
)

class Profile(UserenaBaseProfile):
    user = models.OneToOneField(User)
    first_name = models.CharField(max_length=30)
    middle_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    nickname = models.CharField(max_length=30, default="", blank=True)
    batch = models.ForeignKey('Batch', null=True, blank=True)
    college = models.ForeignKey('College', null=True, blank=True)
    institution = models.CharField(max_length=100, default="")
    mobile_number = models.CharField(max_length=14)
    alternative_email = models.EmailField(blank=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True, null=True)
    primary_interest = models.ForeignKey('PrimaryInterest', null=True, blank=True, limit_choices_to={'children__isnull': True})

    display_full_name = models.CharField(max_length=1, choices=display_full_name_choices,default="N")
    personal_email_unconfirmed = models.EmailField(('unconfirmed email address'),
                                                   blank=True,
                                                   help_text='Temporary email address when the user requests an email change.')
    personal_email_confirmation_key = models.CharField(_('unconfirmed email verification key'),
                                                       max_length=40,
                                                       blank=True)

    personal_email_confirmation_key_created = models.DateTimeField(_('creation date of alternative email confirmation key'),
                                                                   blank=True,
                                                                   null=True)
    session_theme = models.ForeignKey('exams.SessionTheme', null=True, blank=True)

    objects = managers.ProfileManger()

    def __str__(self):
        return self.user.username

    def get_full_name(self):
        # If the first name is missing, let's assume the rest is also
        # missing.
        full_name = ''

        if self.first_name:
            full_name = " ".join([self.first_name, self.middle_name,
                                  self.last_name])
        return full_name

#     ----------------PLAYGROUND----------------------

    def change_personal_email(self, email):
        """
        Changes the email address for a user.

        A user needs to verify this new email address before it becomes
        active. By storing the new email address in a temporary field --
        ``temporary_email`` -- we are able to set this email address after the
        user has verified it by clicking on the verification URI in the email.
        This email gets send out by ``send_verification_email``.

        :param email:
            The new email address that the user wants to use.

        """
        self.personal_email_unconfirmed = email

        salt, confirmation_key = generate_sha1(self.first_name)
        self.personal_email_confirmation_key = confirmation_key
        self.personal_email_confirmation_key_created = get_datetime_now()
        self.save()

        # Send email for activation
        self.send_confirmation_personal_email()

    def send_confirmation_personal_email(self):
        """
        Sends an email to confirm the new email address.

        This method sends out two emails. One to the new email address that
        contains the ``email_confirmation_key`` which is used to verify this
        this email address with :func:`UserenaUser.objects.confirm_email`.

        The other email is to the old email address to let the user know that
        a request is made to change this email address.

        """
        context = {'user': self.user,
                  'without_usernames': userena_settings.USERENA_WITHOUT_USERNAMES,
                  'new_email': self.personal_email_unconfirmed,
                  'protocol': get_protocol(),
                  'confirmation_key': self.personal_email_confirmation_key,
                  'site': Site.objects.get_current()}

        mailer = UserenaConfirmationMail(context=context)
        mailer.generate_mail("confirmation", "_old")

        if self.alternative_email:
            mailer.send_mail(self.alternative_email)

        mailer.generate_mail("confirmation_personal", "_new")
        mailer.send_mail(self.personal_email_unconfirmed)


class PrimaryInterest(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True,
                               related_name="children")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    exam = models.ForeignKey('exams.Exam', null=True, blank=True)
    category = models.ForeignKey('exams.Category', null=True, blank=True)

    objects = managers.PrimaryInterestQuerySet.as_manager()

    def __str__(self):
        return self.name

class Batch(models.Model):
    name = models.CharField(max_length=50)
    college = models.ForeignKey('College')
    complete_number = models.PositiveIntegerField(null=True,
                                                  blank=True)

    def __str__(self):
        return "{} ({} at {})".format(self.name, self.college.name,
                                      self.college.institution.name)

class College(models.Model):
    name = models.CharField(max_length=50)
    institution = models.ForeignKey('Institution')

    def __str__(self):
        return "{} ({})".format(self.name, self.institution.name)


class Institution(models.Model):
    name = models.CharField(max_length=100)
    email_regex = models.CharField(max_length=100, blank=True,
                                   default="")

    def get_total_users(self):
        return self.college_set\
                   .aggregate(total_users=Count('profile'))['total_users']

    def is_email_allowed(self, email):
        if not self.email_regex:
            return True
        else:
            return bool(re.findall(self.email_regex, email, re.I))

    def is_user_allowed(self, user):
        return self.is_email_allowed(user.email)

    def __str__(self):
        return self.name


