from django.db import models
from django.contrib.auth.models import UserManager
from userena.managers import UserenaManager,SHA1_RE
from userena import signals as userena_signals
from userena.utils import generate_sha1
from django.utils.encoding import smart_text
from django.utils.six import text_type

class PrimaryInterestQuerySet(models.QuerySet):
    def meta(self):
        return self.filter(parent__isnull=True)

    def with_children(self):
        return self.filter(children__isnull=False)

    def order_by_alphabet(self):
        return self.order_by('name')

class ProfileManger(UserManager):

    def generate_key_personal_email(self,user):

        if isinstance(user.profile.first_name, text_type):
            user.profile.first_name = smart_text(user.profile.first_name)
        salt, activation_key = generate_sha1(user.profile.first_name)

        try:
            profile = self.filter(user=user)
            profile.update(personal_email_confirmation_key=activation_key)
        except self.model.DoesNotExist:
            raise Exception("Profile doesnt exist")



    def confirm_personal_email(self, confirmation_key):
        """
        Confirm an email address by checking a ``confirmation_key``.

        A valid ``confirmation_key`` will set the newly wanted e-mail
        address as the current e-mail address. Returns the user after
        success or ``False`` when the confirmation key is
        invalid. Also sends the ``confirmation_complete`` signal.

        :param confirmation_key:
            String containing the secret SHA1 that is used for verification.

        :return:
            The verified :class:`User` or ``False`` if not successful.

        """
        if SHA1_RE.search(confirmation_key):
            try:
                userena = self.get(personal_email_confirmation_key=confirmation_key,
                                   personal_email_unconfirmed__isnull=False)
            except self.model.DoesNotExist:
                return False
            else:
                user = userena.user
                old_email = user.profile.alternative_email
                user.profile.alternative_email = userena.personal_email_unconfirmed
                userena.personal_email_unconfirmed, userena.personal_email_confirmation_key = '', ''
                userena.save(using=self._db)
                user.save(using=self._db)

                # Send the confirmation_complete signal
                userena_signals.confirmation_complete.send(sender=None,
                                                           user=user,
                                                           old_email=old_email)

                return user
        return False
