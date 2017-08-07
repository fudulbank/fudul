from django import template
from exams import utils

register = template.Library()

@register.filter
def is_question_marked(question, user):
    return utils.is_question_marked(question, user)

@register.filter
def was_solved_in_session(question, session):
    return question.was_solved_in_session(session)

@register.filter
def was_chosen(choice, session):
    return choice.answer_set.filter(session=session).exists()
