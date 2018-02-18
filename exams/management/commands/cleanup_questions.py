from django.core.management.base import BaseCommand
from django.db.models import Q
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
                       .exclude(~Q(session_mode="INCOMPLETE"),
                                questions__is_deleted=False,
                                questions__revision__is_deleted=False,
                                questions__revision__is_approved=True)\
                       .exclude(session_mode="INCOMPLETE",
                                questions__revision__is_deleted=False)\
                       .update(is_deleted=True)

        sorted_questions = []
        count = 1
        # To give global sequence more stability, we won't exclude
        # deleted question here.
        for question in Question.objects.order_by('pk'):
            # 2) Update the global sequence of questions.
            if not question.is_deleted and \
               not question.revision_set.filter(is_deleted=False).count():
                question.is_deleted = True
                question.save()

            # 3) Update the global sequence of questions.
            if question.pk in sorted_questions:
                continue

            tree = question.get_tree()

            for tree_question in tree:
                if tree_question.global_sequence != count:
                    tree_question.global_sequence = count
                    tree_question.save()
                count += 1
                sorted_questions.append(tree_question.pk)
