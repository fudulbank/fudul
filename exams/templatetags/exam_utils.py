from django import template
from exams import utils, models

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

@register.filter
def get_question_sequence(question, session):
    return session.get_question_sequence(question)

@register.filter
def get_session_url(question, session):
    return question.get_session_url(session)

@register.filter
def show_explanation(question, session):
    if session.session_mode == 'UNEXPLAINED':
        return session.has_finished()
    else:
        return question.was_solved_in_session(session)

@register.filter
def is_editor(category, user):
    if user.is_superuser:
        return True

    while category:
        if category.privileged_teams.filter(members__pk=user.pk).exists():
            return True
        category = category.parent_category

    return False

@register.simple_tag
def get_user_answer_stats(target, user, result, percent=False):
    return utils.get_user_answer_stats(target, user, result, percent)
