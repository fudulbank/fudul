from django.core.management.base import BaseCommand
from exams.models import Question

class Command(BaseCommand):
    help = "Update a global sequence that makes it easy to account for question trees."

    def handle(self, *args, **options):
        finished = []
        count = 1
        for question in Question.objects.order_by('pk'):
            if question.pk in finished:
                continue

            tree = question.get_tree()

            for tree_question in tree:
                tree_question.global_sequence = count
                tree_question.save()
                count += 1
                finished.append(tree_question.pk)
