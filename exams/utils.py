from django.db.models import Count, Q
from exams import models
import teams.utils


def is_question_marked(question, user):
    return question.marking_users.filter(pk=user.pk).exists()

def test_revision_approval(revision):
    return (not revision.submitter or teams.utils.is_editor(revision.submitter)) and \
           not revision.question.issues.filter(is_blocker=True).exists()

def get_only_one_revision_questions():
    return models.Question.objects.annotate(num_revision=Count('revision')).filter(num_revision=1)

def get_contributed_questions(exam):
    pks = models.Revision.objects.per_exam(exam)\
                         .filter(is_contribution=True,
                                 is_deleted=False,
                                 question__is_deleted=False,
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
        queries = Q()
        while deepest_category_level >= count:
            kwarg = {level + '__privileged_teams__members': user}
            level  = level + '__parent_category'
            queries |= Q(**kwarg)
            count += 1
        exams = models.Exam.objects.filter(queries)
    else:
        exams = models.Exam.objects.none()

    return exams

def get_user_question_stats(target, user, result, percent=False):
    # Target can either be an exam, subject or session.
    #
    # Here, two rules kick in:
    #
    # 1) We will display the statistics of questions rather than
    #    answers since it's possible for the same question to have
    #    multiple user answer (i.e. by being part of different
    #    sessions).
    #
    # 2) As a general rule, we will show statistics that are in favor
    #    of the user.  For example, if a question has one correct
    #    answer, then the user got it (regardless of whether it has
    #    other incorrect/skipped answers).
    question_pool = models.Question.objects.approved()\
                                           .used_by_user(user,
                                                         exclude_skipped=False)

    if type(target) is models.Exam:
        question_pool = question_pool.filter(exam=target)
    elif type(target) is models.Subject:
        question_pool = question_pool.filter(subjects=target)
    elif type(target) is models.Session:
        question_pool = question_pool.filter(answer__session=target)

    if result == 'correct':
        count = question_pool.correct_by_user(user)\
                             .count()
    elif result == 'incorrect':
        count = question_pool.incorrect_by_user(user)\
                             .count()
    elif result == 'skipped':
        count = question_pool.skipped_by_user(user)\
                             .count()

    if percent:
        total = question_pool.count()
        if not total:
            return 0
        return "%.0f" % (count / total * 100)
    else:
        return count

def get_exam_question_count_per_meta(exam, meta, approved_only=False):
    if type(meta) is models.Source:
        keyword = 'sources'
    elif type(meta) is models.ExamType:
        keyword = 'exam_types'
    elif type(meta) is models.Subject:
        keyword = 'subjects'
    elif type(meta) is models.Issue:
        keyword = 'issues'

    query = {keyword: meta}

    if approved_only:
        question_pool = exam.question_set.approved()
    else:
        question_pool = exam.question_set
        
    return question_pool.filter(**query).distinct().count()

def get_user_allowed_categories(user):
    categories=[]
    for cat in models.Category.objects.all():
        if cat.can_user_access(user):
            categories.append(cat)
    return categories
