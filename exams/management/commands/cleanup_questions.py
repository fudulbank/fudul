from django.core.management.base import BaseCommand
from exams.models import Question

class Command(BaseCommand):
    help = "Clean-up questions: Update the global sequence and mark questions with zero revisions as deleted."

    def handle(self, *args, **options):
        sorted_questions = []
        count = 1
        # To give global sequence more stability, we won't exclude
        # deleted question here.
        for question in Question.objects.order_by('pk'):
            # If the question is not marked as deleted, but it has
            # zero revisions, mark it as deleted.
            if not question.is_deleted and \
               not question.revision_set.filter(is_deleted=False).count():
                question.is_deleted = True
                question.save()

            if question.pk in sorted_questions:
                continue

            tree = question.get_tree()

            for tree_question in tree:
                if tree_question.global_sequence != count:
                    tree_question.global_sequence = count
                    tree_question.save()
                count += 1
                sorted_questions.append(tree_question.pk)
