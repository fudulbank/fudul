from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db.models import Q, F
from django.utils import timezone
from exams.models import Answer, Question

class Command(BaseCommand):
    help = ("Update correct_user_count, incorrect_user_count and "
            "skipping_user_count fields")

    def handle(self, *args, **options):
        # This process if running once every hour, so any question
        # that hasn't been updated for the past hour, can be scanned.
        one_hour_back = timezone.now() - timedelta(hours=1)
        for question in Question.objects.undeleted()\
                                        .filter(Q(count_update_date__isnull=True) | \
                                                Q(count_update_date__lt=one_hour_back)):
            # If no new answers since last update, skip
            if question.count_update_date and \
               not Answer.objects.filter(question=question,
                                         submission_date__gte=question.count_update_date)\
                                 .exists():
                continue
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
