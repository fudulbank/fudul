from django.core.management.base import BaseCommand
from django.db.models import Q, Count
from exams.models import Session, Question

class Command(BaseCommand):
    help = "Clean-up tasks for the exam app"

    def handle(self, *args, **options):
        # This script does three things:
        #  1) Mark sessions with no accessible questions as deleted.
        #  2) Mark questions with no revisions as deleted.
        #  3) Update the global sequence of questions.

        # 1) Mark sessions with no accessible questions as deleted.
        Session.objects.undeleted()\
               .filter(~Q(session_mode="INCOMPLETE"),
                       questions__is_deleted=False,
                       questions__best_revision__is_approved=True)\
               .annotate(question_count=Count('questions'))\
               .filter(question_count=0)\
               .update(is_deleted=True)
        Session.objects.undeleted()\
                       .filter(session_mode="INCOMPLETE",
                               questions__is_deleted=False)\
                       .annotate(question_count=Count('questions'))\
                       .filter(question_count=0)\
                       .update(is_deleted=True)

        Question.objects.filter(is_deleted=False,
                                revision__is_deleted=False)\
                        .annotate(revision_count=Count('revision'))\
                        .filter(revision_count=0)\
                        .update(is_deleted=True)

        sorted_questions = []
        count = 1
        # To give global sequence more stability, we won't exclude
        # deleted question here.
        for question in Question.objects.select_related('parent_question',
                                                        'child_question')\
                                        .order_by('pk'):
            # Update the global sequence of questions.
            if question.pk in sorted_questions:
                continue

            tree = question.get_tree()

            for tree_question in tree:
                if tree_question.global_sequence != count:
                    tree_question.global_sequence = count
                    tree_question.save()
                count += 1
                sorted_questions.append(tree_question.pk)
