from django.db import models
from accounts.models import College
from django.contrib.auth.models import User

gender_choices = (
    ('F', 'Female'),
    ('M', 'Male'),
)


class Team(models.Model):
    name = models.CharField(max_length=200)
    code_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=1, choices=gender_choices, blank=True,
                              default="")
    college = models.ForeignKey(College, null=True, blank=True,)
    coordinator = models.ForeignKey(User, null=True,
                                    blank=True,
                                    related_name="team_coordination")
    city = models.CharField(max_length=200)
    members = models.ManyToManyField(User,
                                     blank=True,
                                     related_name="team_memberships")
    can_publish = models.BooleanField(default=False)

    def get_member_count(self):
        return self.members.count()

    def __unicode__(self):
        if self.gender and not self.city:
            return u"%s (%s)" % (self.name, self.get_gender_display())
        elif self.city and not self.gender:
            return u"%s (%s)" % (self.name, self.city)
        elif self.city and self.gender:
            return u"%s (%s/%s)" % (self.name, self.city,
                                    self.get_gender_display())
        else:
            return self.name

