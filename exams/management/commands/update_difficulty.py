from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import F, FloatField
from django.db.models.functions import Cast
from exams.models import Exam, Difficulty, Answer, Question


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--verbose', action='store_true',
                            default=False)

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Temporarily disable the statement timeout in production server
            cursor.execute('SET statement_timeout=0;')

            # Updating total_user_count and correct_first_timer_count
            cursor.execute("UPDATE exams_question SET total_user_count=(SELECT COUNT(exams_answer.id) FROM exams_answer INNER JOIN exams_choice ON exams_answer.choice_id=exams_choice.id INNER JOIN exams_session ON exams_answer.session_id=exams_session.id WHERE exams_answer.question_id=exams_question.id AND is_first=TRUE AND exams_answer.choice_id IS NOT NULL);")
            cursor.execute("UPDATE exams_question SET correct_first_timer_count=(SELECT COUNT(exams_answer.id) FROM exams_answer INNER JOIN exams_choice ON exams_answer.choice_id=exams_choice.id WHERE exams_answer.question_id=exams_question.id AND is_first=TRUE AND is_right=TRUE);")

            for difficulty in Difficulty.objects.all():
                if options['verbose']:
                    print(f"Updating {difficulty.label}..")
                cursor.execute(f"UPDATE exams_question SET difficulty_id={difficulty.pk} WHERE ((total_user_count > 0 AND correct_first_timer_count > 0) AND ((correct_first_timer_count::double precision / total_user_count::double precision) * 100) <= {difficulty.upper_limit} AND ((correct_first_timer_count::double precision / total_user_count::double precision) * 100) >= {difficulty.lower_limit});")
            cursor.execute('SET statement_timeout=30000;')
