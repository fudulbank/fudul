from django.core.management.base import BaseCommand
from exams.models import Exam, Revision
import csv
from string import ascii_uppercase

class Command(BaseCommand):
    help = "Update a global sequence that makes it easy to account for question trees."
    def add_arguments(self, parser):
        parser.add_argument('--exam-pk', dest='exam_pk',
                            type=int)

    def handle(self, *args, **options):

        exam_pk = options['exam_pk']
        csv_file = open('export-exam-%s.csv' % exam_pk, 'w')
        csv_writer = csv.writer(csv_file)
        exam = Exam.objects.get(pk=exam_pk)
        revisions = Revision.objects.per_exam(exam)\
                                    .filter(is_last=True)\
                                    .select_related('question', 'question__parent_question')\
                                    .order_by('question__pk')

        header = ['ID', 'Text', 'Choice A', 'Choice B', 'Choice C',
                  'Choice D', 'Choice E', 'Answer', 'Explanation',
                  'Parent question', 'Exam type', 'Issues', 'Subject',
                  'Source']

        csv_writer.writerow(header)

        for revision in revisions:
            pk = revision.question.pk
            text = revision.text
            choice_texts = []
            right_answer = ''
            choice_index = 0
            for choice in revision.choice_set.order_by_alphabet():
                choice_texts.append(choice.text)
                if choice.is_right:
                    right_answer = ascii_uppercase[choice_index]
                choice_index += 1

            if len(choice_texts) < 5:
                remaining = 5 - len(choice_texts)
                choice_texts = choice_texts + ([''] * remaining)

            explanation = revision.explanation
            if revision.question.parent_question:
                parent_question_pk = revision.question.parent_question.pk
            else:
                parent_question_pk = ""
            exam_types = ", ".join([exam_type.name for exam_type in revision.question.exam_types.all()])
            issues = ", ".join([issue.name for issue in revision.question.issues.all()])
            subjects = ", ".join([subject.name for subject in revision.question.subjects.all()])
            sources = ", ".join([source.name for source in revision.question.sources.all()])

            row = [pk, text] + choice_texts + [right_answer, explanation, parent_question_pk] + \
                  [exam_types, issues, subjects, sources]

            csv_writer.writerow(row)

        csv_file.close()
