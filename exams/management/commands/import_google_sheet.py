from django.core.management.base import BaseCommand
from exams import models
from string import ascii_uppercase
import csv


class Command(BaseCommand):
    help = "Update a global sequence that makes it easy to account for question trees."
    def add_arguments(self, parser):
        parser.add_argument('--csv-path', dest='csv_path',
                            type=str)
        parser.add_argument('--exam-pk', dest='exam_pk',
                            type=str)
        parser.add_argument('--sequence', dest='sequence',
                            type=int, default=None)
        parser.add_argument('--disapproved', dest='is_disapproved',
                            action='store_true', default=False)

    def handle(self, *args, **options):
        csv_file = open(options['csv_path'])
        csv_reader = csv.reader(csv_file)
        exam = models.Exam.objects.get(pk=options['exam_pk'])
        subject_pool = exam.subject_set.all()
        exam_type_pool = exam.exam_types.all()
        final_exam_type = exam_type_pool.get(name="Final")
        source_pool = exam.get_sources()
        status_pool = models.Status.objects.all()
        unclassified_source = source_pool.get(name="Unclassified")

        # The latest question imported is initially None.
        question = None

        # Skip headers
        next(csv_reader)

        for row in csv_reader:
            # We will only mark imported revision as a apporved if a
            # right answer was specified.
            is_approved = False
            sequence = int(row[0])
            print("Handling %d..." % sequence)
            if options['sequence'] and \
               options['sequence'] > sequence:
                continue
            text = row[1].strip()
            if not text:
                continue
            choices = [models.Choice(text=choice.strip()) for choice in row[2:7] if choice.strip()]

            # Check if the right answer column is filled
            if row[7]:
                try:
                    answer_index = ascii_uppercase.index(row[7])
                    print("Right answer is %s (%s)"  % (row[7], choices[answer_index].text))
                    choices[answer_index].is_right = True
                    if not options['is_disapproved']:
                        is_approved = True
                except (IndexError, ValueError):
                    # If the no proper right asnwer was specified, or
                    # if the chosen answer falls outside the range of
                    # possible choices, the revision's
                    # is_approved=False
                    pass


            # We use subject/source/exam_type pools with a somewhat
            # weird way for fetching objects to optimize the code and
            # avoid insane number of database hits.

            subject_entries = [entry.strip().lower() for entry in row[8:12] if entry.strip()]
            print("Subjects:", ",".join(subject_entries))
            subjects = [subject for subject in subject_pool if subject.name.lower() in subject_entries]

            source_entry = row[12].strip().lower()
            print("Source:", source_entry)
            if source_entry:
                source = [source for source in source_pool if source.name.lower() == source_entry][0]
            else:
                source = unclassified_source

            exam_type_entry = row[13].strip().lower()
            print("Exam type:", exam_type_entry)
            if exam_type_entry:
                exam_type = [exam_type for exam_type in exam_type_pool if exam_type.name.lower() == exam_type_entry][0]
            else:
                # The collectors were instructed to mark questions
                # with unknown type as 'Final'.  We are doing the same
                # here.
                exam_type = final_exam_type

            status_entries = [entry.strip() for entry in row[14:16] if entry.strip()]
            print("Statuses:", ",".join(status_entries))
            statuses = [status for status in status_pool if status.name in status_entries]

            # If parent_question is specified, it is VERY LIKELY to be
            # the latest imported revision

            parent_question_pk = row[16] or None
            if parent_question_pk:
                parent_question = question
            else:
                parent_question = None

            try:
                reference = row[17]
            except IndexError:
                # Not all Google Sheets have references
                reference = ""
    
            question = models.Question.objects.create(exam=exam,
                                                      parent_question=parent_question)
            question.subjects.add(*subjects)
            question.exam_types.add(exam_type)
            question.sources.add(source)
            question.statuses.add(*statuses)
            revision = models.Revision.objects.create(question=question,
                                                      text=text,
                                                      reference=reference,
                                                      change_summary="Imported from Google Sheets",
                                                      is_approved=is_approved,
                                                      is_first=True,
                                                      is_last=True)
            for choice in choices:
                choice.revision = revision

            models.Choice.objects.bulk_create(choices)
