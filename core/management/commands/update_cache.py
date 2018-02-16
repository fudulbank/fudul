from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.cache import cache
from exams.models import *
import exams.utils

class Command(BaseCommand):
    def handle(self, *args, **options):
        # HOME PAGE
        sample_question = cache.get('sample_question')
        if not sample_question:
            # To give a less confusing expereince, exclude any question with
            # correction.
            sample_question = Question.objects.approved()\
                                              .filter(answer__isnull=False,
                                                      parent_question__isnull=True,
                                                      child_question__isnull=True)\
                                              .exclude(revision__choice__answer_correction__isnull=False)\
                                              .distinct()\
                                              .order_by('?')\
                                              .first()
            cache.set('sample_question', sample_question,
                      settings.CACHE_PERIODS['EXPENSIVE_UNCHANGEABLE'])

        question_count = Question.objects.undeleted().count()
        cache.set('question_count', question_count, None)

        answer_count = Answer.objects.filter(choice__isnull=False)\
                                     .count()
        cache.set('answer_count', answer_count, None)

        correct_percentage = exams.utils.get_correct_percentage()
        cache.set('correct_percentage', correct_percentage, None)
