from django.db import models
from django.contrib.auth.models import User

class Team(models.Model):
    name = models.CharField(max_length=200)
    code_name = models.CharField(max_length=200)
    members = models.ManyToManyField(User,
                                     blank=True,
                                     related_name="team_memberships")
    categories = models.ManyToManyField('exams.Category',
                                        related_name="privileged_teams")
    access_choices = (
        ('editors', 'Editors'),
        ('collectors', 'Collectors')
        )
    access = models.CharField(max_length=10, choices=access_choices,default='')

    def get_member_count(self):
        return self.members.count()

    def __str__(self):
        return self.name
