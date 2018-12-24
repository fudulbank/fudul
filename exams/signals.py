from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender='exams.Revision')
def update_latest_revision(sender, instance, **kwargs):
    question = instance.question

    # Update is_last field:
    latest_revision = question.get_latest_revision()
    if latest_revision:
        question.revision_set.exclude(pk=latest_revision.pk)\
                         .update(is_last=False)
        if not latest_revision.is_last:
            latest_revision.is_last = True
            latest_revision.save()

    # Mark delete a question as such: 
    if not question.revision_set.undeleted().count():
        question.is_deleted = True
        question.save()

    # Update best_revision field:
    best_revision = question.get_best_revision()
    question.best_revision = best_revision

    # Update approval status:
    approved_revision = question.get_latest_approved_revision()
    if approved_revision and \
       not question.is_deleted and \
       not question.issues.filter(is_blocker=True).exists() and \
       approved_revision.choice_set.filter(is_right=True).exists() and \
       approved_revision.choice_set.count() > 1:
        question.is_approved = True
    else:
        question.is_approved = False

    question.save()

@receiver([post_save, post_delete], sender='exams.ExplanationRevision')
def update_latest_explanation_revision(sender, instance, **kwargs):
    question = instance.question

    latest_explanation_revision = question.get_latest_explanation_revision()
    if latest_explanation_revision:
        question.explanation_revisions.exclude(pk=latest_explanation_revision.pk)\
                                  .update(is_last=False)
        if not latest_explanation_revision.is_last:
            latest_explanation_revision.is_last = True
            latest_explanation_revision.save()

        question.latest_explanation_revision = latest_explanation_revision
        question.save()
