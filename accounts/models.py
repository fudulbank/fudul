from django.db import models
from django.db.models import Count
from django.contrib.auth.models import User
import re
from userena.models import UserenaBaseProfile
from django.utils.translation import ugettext as _

class Profile(UserenaBaseProfile):
    user = models.OneToOneField(User)
    first_name = models.CharField(max_length=30)
    middle_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    nickname = models.CharField(max_length=30)
    batch = models.ForeignKey('Batch', null=True, blank=True)
    college = models.ForeignKey('College', null=True, blank=True)
    institution = models.CharField(max_length=100, default="")
    mobile_number = models.CharField(max_length=14)
    alternative_email = models.EmailField(blank=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True, null=True)

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

class Batch(models.Model):
    name = models.CharField(max_length=50)
    college = models.ForeignKey('College')
    complete_number = models.PositiveIntegerField(null=True)

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


