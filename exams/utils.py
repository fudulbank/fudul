import teams.utils
from exams.models import Question,Revision
from django.db.models import Count

def is_question_marked(question, user):
    return question.marking_users.filter(pk=user.pk).exists()


def is_question_complete(question):
    return question.get_latest_revision().statuses.filter(code_name="COMPLETE").exists()


def test_revision_approval(revision):
    return teams.utils.is_editor(revision.submitter) and \
           revision.statuses.filter(code_name='COMPLETE').exists() and \
           revision.choice_set.count() >= 2


def get_only_one_revision_questions():
    return Question.objects.annotate(num_revision=Count('revision')).filter(num_revision=1)

def get_contributed_questions(exam):
    pks = Revision.objects.per_exam(exam) \
        .filter(is_contribution=True,is_deleted=False,is_approved=False) \
        .values_list('question__pk', flat=True)
    questions = get_only_one_revision_questions().filter(pk__in=pks)
    return questions

