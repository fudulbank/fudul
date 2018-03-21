from django import template
from django.db.models import Q
from exams import utils, models

register = template.Library()

@register.filter
def has_changed_choices(revision, previous_revision):
    previous_choice_texts = previous_revision.choice_set\
                                             .values_list('text')
    new_choice_texts = revision.choice_set\
                               .values_list('text')
    return revision.choice_set\
                   .exclude(text__in=previous_choice_texts)\
                   .exists() or \
           previous_revision.choice_set\
                            .exclude(text__in=new_choice_texts)\
                            .exists()

@register.filter
def get_choice_pairs(revision, previous_revision):
    index = 0
    for new_choice in revision.choice_set.order_by_alphabet():
        try:
            previous_choice = previous_revision.choice_set.order_by_alphabet()[index]
        except IndexError:
            previous_choice_text = ''
        else:
            previous_choice_text = previous_choice.text
        yield new_choice.text, previous_choice_text, new_choice.is_right
        index += 1

@register.filter
def get_question_sequence(question, session):
    return session.get_question_sequence(question)

@register.filter
def can_user_edit(exam, user):
    return exam.can_user_edit(user)

@register.filter
def get_meta_exam_question_count(exam, meta):
    return utils.get_meta_exam_question_count(exam, meta)

@register.filter
def order_by_exam_questions(meta_queryset, exam):
    # 'meta_queryset' can be a queryset of any of: Source, Subject or
    # ExamType.  All of which share the same Manager.
    return meta_queryset.order_by_exam_questions(exam)

@register.filter
def was_ever_taken_by_user(exam, user):
    return exam.session_set.filter(submitter=user).exists()

@register.filter
def get_used_question_count_per_user(exam, user):
    return exam.question_set.approved()\
                            .used_by_user(user,
                                          exclude_skipped=False)\
                            .count()

@register.simple_tag
def get_user_question_stats(target, user, result, total=None, percent=False):
    return utils.get_user_question_stats(target, user, result, total, percent)

@register.filter
def get_session_subjects(session):
    return session.subjects.all() or session.exam.subject_set.all()

@register.filter
def get_exam_question_count_per_meta(exam, meta, approved_only=False):
    return utils.get_exam_question_count_per_meta(exam, meta, approved_only)

@register.filter
def can_support_correction(user, correction):
    return correction.submitter != user and not correction.supporting_users.filter(pk=user.pk).exists()

@register.filter
def can_oppose_correction(user, correction):
    return correction.submitter != user and not correction.opposing_users.filter(pk=user.pk).exists()

@register.filter
def can_delete_correction(user, correction):
    return correction.can_user_delete(user)

@register.filter
def can_user_access(user, obj):
    return obj.can_user_access(user)

@register.filter
def get_question_created_count(user, question_pool=None):
    if not question_pool:
        question_pool = models.Question.objects\
                                       .undeleted()

    return question_pool.filter(revision__is_first=True,
                                revision__is_deleted=False,
                                revision__submitter=user)\
                        .distinct().count()

@register.filter
def get_question_edited_count(user, question_pool=None):
    if not question_pool:
        question_pool = models.Question.objects\
                                       .undeleted()

    return question_pool.exclude(revision__is_first=True,
                                 revision__is_deleted=False,
                                 revision__submitter=user)\
                        .filter(revision__is_first=False,
                                revision__is_deleted=False,
                                revision__submitter=user)\
                        .distinct().count()

@register.filter
def get_question_assigned_count(user, question_pool=None):
    if not question_pool:
        question_pool = models.Question.objects\
                                       .undeleted()

    return question_pool.filter(assigned_editor=user).count()

@register.filter
def is_mnemonic_submiiter(mnemonic,user):
    if mnemonic.submitter == user :
        return True

@register.filter
def get_pending_action_count(user):
    change_count = models.SuggestedChange.objects.filter(status="PENDING", revision__question__exam__privileged_teams__members=user)
    duplicate_count = models.DuplicateContainer.objects.filter(status="PENDING", primary_question__exam__privileged_teams__members=user)
    return change_count.count() + duplicate_count.count()
