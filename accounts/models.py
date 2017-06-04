from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User)
    first_name = models.CharField(max_length=30)
    middle_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    college = models.ForeignKey('College', null=True)
    mobile_number = models.CharField(max_length=14)
    alternative_email = models.EmailField(blank=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.user.username

    def get_full_name(self):
        try:
            # If the first name is missing, let's assume the rest is
            # also missing.
            if self.first_name:
                ar_fullname = " ".join([self.first_name,
                                        self.middle_name,
                                        self.last_name])
        except AttributeError: # If the user has their details missing
            pass

        return fullname

class College(models.Model):
    name = models.CharField(max_length=50)
    institution = models.ForeignKey('Institution')

    def __str__(self):
        return self.name

class Institution(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
