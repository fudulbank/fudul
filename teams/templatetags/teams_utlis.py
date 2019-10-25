from django import template
from teams import utils
from exams import models as exam_models

register = template.Library()

@register.filter
def is_editor(user):
    return utils.is_editor(user)

@register.filter
def is_examiner(user):
    return utils.is_examiner(user)

@register.filter
def get_user_privileged_exams(user):
    return exam_models.Exam.objects.filter(privileged_teams__members=user)\
                                   .distinct()

@register.filter
def get_user_privileged_triggers(user):
    return exam_models.Trigger.objects.filter(exam__privileged_teams__members=user)\
                                      .distinct()
