from django.core.management.base import BaseCommand
from django.db.models import Q, F
from django.utils import timezone
from exams.models import Answer, Session, Question

class Command(BaseCommand):
    help = ("Update correct_user_count, incorrect_user_count and "
            "skipping_user_count fields")

    def handle(self, *args, **options):
        for question in Question.objects.undeleted()\
                                        .filter(Q(count_update_date__isnull=True) | \
                                                Q(count_update_date__lt=F('answer__submission_date')))\
                                        .distinct():
            total_user_count = Answer.objects.filter(question=question)\
                                             .values_list('session__submitter', flat=True)\
                                             .distinct().count()

            correct_user_pks = Answer.objects.filter(question=question,
                                                     choice__is_right=True)\
                                             .values_list('session__submitter', flat=True)\
                                             .distinct()
            incorrect_user_pks = Answer.objects.filter(question=question,
                                                       choice__is_right=False)\
                                               .values_list('session__submitter', flat=True)\
                                               .distinct()
            skipping_user_pks = Answer.objects.filter(question=question,
                                                      choice__isnull=True)\
                                              .values_list('session__submitter', flat=True)\
                                              .distinct()

            # Get counts
            correct_user_count = len(correct_user_pks)
            incorrect_user_count = len([pk for pk in
                                        incorrect_user_pks if pk not
                                        in correct_user_pks])
            skipping_user_count = len([pk for pk in skipping_user_pks
                                       if pk not in correct_user_pks
                                       and pk not in
                                       incorrect_user_pks])

            question.total_user_count = total_user_count
            question.correct_user_count = correct_user_count
            question.incorrect_user_count = incorrect_user_count
            question.skipping_user_count = skipping_user_count
            question.count_update_date = timezone.now()

            question.save()
