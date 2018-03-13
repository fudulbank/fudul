from django import template
from teams import utils
from exams import models as exam_models

register = template.Library()

@register.filter
def is_editor(user):
    return utils.is_editor(user)

@register.filter
def get_user_privileged_exams(user):
    return exam_models.Exam.objects.filter(privileged_teams__members=user)\
                                   .distinct()
