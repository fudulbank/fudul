import teams.utils
from exams import models
from django.db.models import Count

def is_question_marked(question, user):
    return question.marking_users.filter(pk=user.pk).exists()


def is_question_complete(question):
    return question.get_latest_revision().statuses.filter(code_name="COMPLETE").exists()


def test_revision_approval(revision, submitter):
    return teams.utils.is_editor(submitter) and \
           revision.statuses.filter(code_name='COMPLETE').exists() and \
           revision.choice_set.count() >= 2


def get_only_one_revision_questions():
    return models.Question.objects.annotate(num_revision=Count('revision')).filter(num_revision=1)

def get_contributed_questions(exam):
    pks = models.Revision.objects.per_exam(exam) \
        .filter(is_contribution=True,is_deleted=False,is_approved=False) \
        .values_list('question__pk', flat=True)
    questions = get_only_one_revision_questions().filter(pk__in=pks)
    return questions

def get_user_answer_stats(target, user, result, percent=False):
    answer_pool = models.Answer.objects.filter(session__submitter=user)\
                                       .distinct()
    if type(target) is models.Exam:
        answer_pool = answer_pool.filter(session__exam=target)
    elif type(target) is models.Subject:
        answer_pool = answer_pool.filter(question__subjects=target)

    if result == 'correct':
        count = answer_pool.filter(choice__is_right=True).count()
    elif result == 'incorrect':
        count = answer_pool.filter(choice__is_right=False).count()
    elif result == 'skipped':
        count = answer_pool.filter(choice__isnull=True).count()

    if percent:
        total = answer_pool.count()
        return "%.0f" % (count / total * 100)
    else:
        return count
