from django.db import models
from django.contrib.auth.models import User
import exams.models

def get_name(self):
    if hasattr(self, 'profile'):
        return self.profile.get_full_name()
    else:
        return self.username

User.add_to_class("__str__", get_name)

class Team(models.Model):
    name = models.CharField(max_length=200)
    code_name = models.CharField(max_length=200)
    members = models.ManyToManyField(User,
                                     blank=True,
                                     related_name="team_memberships")
    exams = models.ManyToManyField('exams.Exam',
                                   related_name="privileged_teams")
    is_examiner = models.BooleanField('This group represents a group of examiners',
                                      default=False)

    def get_member_count(self):
        return self.members.count()
    get_member_count.short_description = 'Member count'

    def get_question_count(self):
        return exams.models.Question.objects\
                                    .filter(exam__in=self.exams.all())\
                                    .undeleted()\
                                    .distinct()\
                                    .count()

    def __str__(self):
        return self.name
