from django.db.models import Count, Q
from exams import models
import teams.utils


def is_question_marked(question, user):
    return question.marking_users.filter(pk=user.pk).exists()


def is_question_complete(question):
    return question.get_latest_revision().statuses.filter(code_name="COMPLETE").exists()


def test_revision_approval(revision):
    return teams.utils.is_editor(revision.submitter) and \
           revision.statuses.filter(code_name='COMPLETE').exists() and \
           revision.choice_set.count() >= 2


def get_only_one_revision_questions():
    return models.Question.objects.annotate(num_revision=Count('revision')).filter(num_revision=1)

def get_contributed_questions(exam):
    pks = models.Revision.objects.per_exam(exam)\
                         .filter(is_contribution=True,
                                 is_deleted=False,
                                 is_approved=False)\
                         .values_list('question__pk',
                                      flat=True)
    questions = get_only_one_revision_questions().filter(pk__in=pks)
    return questions

def get_deepest_category_level():
    count = 1
    level = 'parent_category__isnull'
    kwargs = {level: False}
    while models.Category.objects.filter(**kwargs).exists():
        level  = 'parent_category__' + level
        kwargs[level] = False
        count += 1
    return count

def get_user_privileged_exams(user):
    if user.is_superuser:
        exams = models.Exam.objects.all()
    elif teams.utils.is_editor(user):
        deepest_category_level = get_deepest_category_level()
        count = 1
        level = 'category'
        querys = Q()
        while deepest_category_level >= count:
            kwarg = {level + '__privileged_teams__members': user}
            level  = level + '__parent_category'
            querys |= Q(**kwarg)
            count += 1
        exams = models.Exam.objects.filter(querys)
    else:
        exams = models.Exam.objects.none()

    return exams
