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

def get_user_question_stats(target, user, result, total=None, percent=False):
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
    # Subject and Exam models have a similar way of calculation.
    if type(target) in [models.Subject, models.Exam]:
        if type(target) is models.Exam:
            all_pks = models.Answer.objects.filter(session__submitter=user,
                                                   question__exam=target,
                                                   session__is_deleted=False)\
                                           .values('question')
            pool = models.Question.objects.undeleted().filter(exam=target)
        elif type(target) is models.Subject:
            all_pks = models.Answer.objects.filter(session__submitter=user,
                                                   question__subjects=target,
                                                   session__is_deleted=False)\
                                           .values('question')
            pool = models.Question.objects.undeleted().filter(subjects=target)

        if result == 'correct':
            count = pool.correct_by_user(user)\
                        .count()
        elif result == 'incorrect':
            count = pool.incorrect_by_user(user)\
                        .count()
        elif result == 'skipped':
            count = pool.skipped_by_user(user)\
                        .count()
        elif result == 'total':
            count = pool.filter(pk__in=all_pks).count()
    elif type(target) is models.Session:
        pool = models.Answer.objects.filter(session=target)\
                                    .of_undeleted_questions()\
                                    .distinct()
        if result == 'correct':
            count = target.get_correct_count()
        elif result == 'incorrect':
            count = target.get_incorrect_count()
        elif result == 'skipped':
            count = target.get_skipped_count()
        elif result == 'total':
            count = pool.count()

    if percent:
        # If total was not provided
        if total is None or total == '':
            total = pool.count()
        if total == 0:
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


def get_correct_percentage():
    # How many questions are considered "recent"?
    RECENT_COUNT = 100

    try:
        recent_answer = models.Answer.objects.filter(choice__isnull=False)\
                                     .order_by('-submission_date')[RECENT_COUNT - 1]
    except IndexError:
        recent_answer = models.Answer.objects.first()
    correct_count = models.Answer.objects.filter(submission_date__gte=recent_answer.submission_date,
                                                 choice__isnull=False,
                                                 choice__is_right=True)\
                                         .count()

    correct_percentage = correct_count / RECENT_COUNT
    correct_percentage = round(correct_percentage, 3) * 100

    return correct_percentage
