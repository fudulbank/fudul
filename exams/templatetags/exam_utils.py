from django import template
from exams import utils

register = template.Library()

@register.filter
def is_question_marked(question, user):
    return utils.is_question_marked(question, user)
