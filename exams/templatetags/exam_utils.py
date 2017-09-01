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

@register.filter
def get_meta_exam_question_count(exam, meta):
    if type(meta) is models.Source:
        keyword = 'sources'
    elif type(meta) is models.ExamType:
        keyword = 'exam_types'
    elif type(meta) is models.Subject:
        keyword = 'subjects'

    query = {keyword: meta}

    return exam.question_set.filter(**query).distinct().count()

@register.filter
def order_by_exam_questions(meta_queryset, exam):
    # 'meta_queryset' can be a queryset of any of: Source, Subject or
    # ExamType.  All of which share the same Manager.
    return meta_queryset.order_by_exam_questions(exam)

@register.filter
def was_ever_taken_by_user(exam, user):
    return exam.session_set.filter(submitter=user).exists()

@register.filter
def get_user_answered_question_count(exam, user):
    return exam.get_user_answered_questions(user).count()

@register.simple_tag
def get_user_answer_stats(target, user, result, percent=False):
    return utils.get_user_answer_stats(target, user, result, percent)

@register.filter
def get_session_subjects(session):
    return session.subjects.distinct() | session.exam.subject_set.distinct()
