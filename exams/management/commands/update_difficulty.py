from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
from django.db.models import F, FloatField
from django.db.models.functions import Cast
from exams.models import Exam, Difficulty, Answer, Question


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--verbose', action='store_true',
                            default=False)
        parser.add_argument('--force', action='store_true',
                            default=False)

    def handle(self, *args, **options):
        difficulties = Difficulty.objects.all()
        with connection.cursor() as cursor:
            # Temporarily disable the statement timeout in production server
            if not settings.DEBUG:
                cursor.excute('SET statement_timeout=0;')

            # Updating total_user_count and correct_first_timer_count
            cursor.execute("UPDATE exams_question SET total_user_count=(SELECT COUNT(exams_answer.id) FROM exams_answer INNER JOIN exams_choice ON exams_answer.choice_id=exams_choice.id INNER JOIN exams_session ON exams_answer.session_id=exams_session.id WHERE exams_answer.question_id=exams_question.id AND is_first=TRUE AND exams_answer.choice_id IS NOT NULL);")
            cursor.execute("UPDATE exams_question SET correct_first_timer_count=(SELECT COUNT(exams_answer.id) FROM exams_answer INNER JOIN exams_choice ON exams_answer.choice_id=exams_choice.id WHERE exams_answer.question_id=exams_question.id AND is_first=TRUE AND is_right=TRUE);")
            if not settings.DEBUG:
                cursor.excute('SET statement_timeout=30000;')

            for difficulty in difficulties:
                question_pool = Question.objects.available()\
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
                    print(f"Nothing for {difficulty.label}.")
