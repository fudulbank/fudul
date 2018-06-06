from django.core.management.base import BaseCommand
from exams.models import *
from string import ascii_uppercase
import csv


class Command(BaseCommand):
    help = "Update a global sequence that makes it easy to account for question trees."
    def add_arguments(self, parser):
        parser.add_argument('--csv-path',
                            type=str)
        parser.add_argument('--default-source-name',
                            type=str, default=None)
        parser.add_argument('--default-exam-type-name',
                            type=str, default=None)
        parser.add_argument('--exam-pk',
                            type=str)
        parser.add_argument('--skip-until',
                            type=int, default=None)
        parser.add_argument('--disapproved', dest='is_disapproved',
                            action='store_true', default=False)
        parser.add_argument('--dry', action='store_true',
                            default=False)

    def handle(self, *args, **options):
        csv_file = open(options['csv_path'])
        csv_reader = csv.reader(csv_file)
        exam = Exam.objects.get(pk=options['exam_pk'])
        subject_pool = exam.subject_set.all()
        exam_type_pool = exam.exam_types.all()
        source_pool = exam.get_sources()
        issue_pool = Issue.objects.all()

        if options['default_exam_type_name']:
            default_exam_type = exam_type_pool.get(name=options['default_exam_type_name'])
        else:
            default_exam_type = None

        if options['default_source_name']:
            default_source = source_pool.get(name=options['default_source_name'])
        else:
            default_source = None

        # ROW DISTRIBUTION
        COL_SEQUENCE = 0
        COL_TEXT = 1
        COL_CHOICE_START = 2
        COL_CHOICE_END = 7
        COL_ANSWER = 8
        COL_SUBJECT_START = 9
        COL_SUBJECT_END = 12
        COL_SOURCE = 13
        COL_EXAM_TYPE = 14
        COL_ISSUE_START = 15
        COL_ISSUE_END = 16
        COL_PARENT_QUESTION = 17
        COL_EXPLANATION = 18
        COL_REFERENCE = 19

        # The latest question imported is initially None.
        question = None

        # Skip headers
        next(csv_reader)

        for row in csv_reader:
            # We will only mark imported revision as a apporved if a
            # right answer was specified.
            is_approved = False
            sequence = int(row[COL_SEQUENCE])
            print("Handling %d..." % sequence)
            if options['skip_until'] and \
               options['skip_until'] > sequence:
                continue
            text = row[COL_TEXT].strip()
            if not text:
                continue
            choices = [Choice(text=choice.strip()) for choice in row[COL_CHOICE_START:COL_CHOICE_END + 1] if choice.strip()]

            # Check if the right answer column is filled
            if COL_ANSWER:
                try:
                    answer = row[COL_ANSWER].upper()
                    answer_index = ascii_uppercase.index(answer)
                    print("Right answer is %s (%s)"  % (row[COL_ANSWER], choices[answer_index].text))
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

            subject_entries = [entry.strip().lower() for entry in row[COL_SUBJECT_START:COL_SUBJECT_END + 1] if entry.strip()]
            print("Subjects:", ",".join(subject_entries))
            subjects = [subject for subject in subject_pool if subject.name.lower() in subject_entries]

            source_entry = row[COL_SOURCE].strip().lower()
            print("Source:", source_entry)
            if source_entry:
                source = [source for source in source_pool if source.name.lower() == source_entry][0]
            elif default_source:
                source = default_source
            else:
                source = None

            exam_type_entry = row[COL_EXAM_TYPE].strip().lower()
            print("Exam type:", exam_type_entry)
            if exam_type_entry:
                exam_type = [exam_type for exam_type in exam_type_pool if exam_type.name.lower() == exam_type_entry][0]
            elif default_exam_type:
                exam_type = default_exam_type
            else:
                exam_type = None

            issue_entries = [entry.strip() for entry in row[COL_ISSUE_START:COL_ISSUE_END + 1] if entry.strip()]
            print("Issues:", ",".join(issue_entries))
            issues = [issue for issue in issue_pool if issue.name in issue_entries]

            # If parent_question is specified, it is VERY LIKELY to be
            # the latest imported revision

            parent_question_pk = row[COL_PARENT_QUESTION] or None
            if parent_question_pk:
                parent_question = question
            else:
                parent_question = None

            try:
                explanation = row[COL_EXPLANATION]
            except IndexError:
                # Not all Google Sheets have explanations
                explanation = ""

            try:
                reference = row[COL_REFERENCE]
            except IndexError:
                # Not all Google Sheets have references
                reference = ""

            if not options['dry']:
                question = Question.objects.create(exam=exam,
                                                   is_approved=is_approved,
                                                   parent_question=parent_question)
                question.subjects.add(*subjects)
                question.issues.add(*issues)
                if source:
                    question.sources.add(source)
                if exam_type:
                    question.exam_types.add(exam_type)

                revision = Revision.objects.create(question=question,
                                                   text=text,
                                                   change_summary="Imported from Google Sheets",
                                                   is_approved=is_approved,
                                                   is_first=True,
                                                   is_last=True)
                if explanation:
                    ExplanationRevision.objects.create(question=question,
                                                       is_first=True,
                                                       is_last=True,
                                                       reference=reference,
                                                       explanation_text=explanation)

                for choice in choices:
                    choice.revision = revision

                Choice.objects.bulk_create(choices)
                question.best_revision = revision
                question.save()
