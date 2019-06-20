from django.core.management.base import BaseCommand
from django.db.models import F, FloatField
from django.db.models.functions import Cast
from exams.models import Exam, Difficulty, Answer


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--verbose', action='store_true',
                            default=False)
        parser.add_argument('--force', action='store_true',
                            default=False)

    def handle(self, *args, **options):
        difficulties = Difficulty.objects.all()
        for exam in Exam.objects.all():
            # If no answer was submitted to this exam since it was
            # last evaluated, save the trouble of updating the
            # difficulty.
            last_answer = Answer.objects.filter(session__exam=exam)\
                                        .order_by('pk').last()
            if not options['force'] and \
               (not last_answer or \
                exam.last_answer_for_difficulty == last_answer):
                continue

            for question in exam.question_set.available():
                total_users = Answer.objects.filter(question=question)\
                                            .values('session__submitter_id')\
                                            .distinct()\
                                            .count()
                correct_first_timers = Answer.objects.filter(choice__is_right=True,
                                                             is_first=True,
                                                             question=question)\
                                                     .values('session__submitter_id')\
                                                     .distinct()\
                                                     .count()                
                if question.total_user_count != total_users or \
                   question.correct_first_timer_count != correct_first_timers:
                    question.total_user_count = total_users
                    question.correct_first_timer_count = correct_first_timers
                    if options['verbose']:
                        print(f"Updating counts for Q#{question.pk} ({total_users}, {correct_first_timers})...")
                    question.save()
                elif options['verbose']:
                    print(f"Nothing to be done for Q#{question.pk}.")

            for difficulty in difficulties:
                question_pool = exam.question_set.available()\
                                                 .filter(total_user_count__gt=0,
                                                         correct_first_timer_count__gt=0)\
                                                 .annotate(correct_percentage=Cast(F('correct_first_timer_count'), FloatField()) / Cast(F('total_user_count'), FloatField()) * 100)
                if difficulty.upper_limit:
                    question_pool = question_pool.filter(correct_percentage__lte=difficulty.upper_limit)
                if difficulty.lower_limit:
                    question_pool = question_pool.filter(correct_percentage__gte=difficulty.lower_limit)

                pool_count = question_pool.count()
                if pool_count:
                    if options['verbose']:
                        print(f"Updating {pool_count} with {difficulty.label}")

                    question_pool.update(difficulty=difficulty)
                elif options['verbose']:
                    print(f"Nothing for {difficulty.label} in {exam.name}")
            exam.last_answer_for_difficulty = last_answer
            exam.save()
