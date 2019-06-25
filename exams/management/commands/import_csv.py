from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from exams.models import *
from string import ascii_uppercase
import csv

# We use subject/source/exam_type pools with a somewhat
# weird way for fetching objects to optimize the code and
# avoid insane number of database hits.

def light_get_from_pool(pool, name):
    # Clean the name
    name = name.strip().lower()
    # If no name is given, exit
    if not name:
        return
    for i in pool:
        if i.name.lower() == name:
            return i

class Command(BaseCommand):
    help = "Update a global sequence that makes it easy to account for question trees."
    def add_arguments(self, parser):
        parser.add_argument('--csv-path',
                            type=str)
        parser.add_argument('--default-subject',
                            type=str, default=None)
        parser.add_argument('--default-source',
                            type=str, default=None)
        parser.add_argument('--default-exam-type',
                            type=str, default=None)
        parser.add_argument('--exam-pk',
                            type=str)
        parser.add_argument('--submitter-email',
                            type=str, default=None)
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
        added_pks = [] 

        if options['submitter_email']:
            submitter = User.objects.get(email__iexact=options['submitter_email'])
        else:
            submitter = None

        if options['default_exam_type']:
            default_exam_type = exam_type_pool.get(name=options['default_exam_type'])
        else:
            default_exam_type = None

        if options['default_source']:
            default_source = source_pool.get(name=options['default_source'])
        else:
            default_source = None

        if options['default_subject']:
            default_subject = subject_pool.get(name=options['default_subject'])
        else:
            default_subject = None

        headers = next(csv_reader)

        INDEXES = {'SEQUENCE': None,
                   'QUESTION_TEXT': None,
                   'ANSWER': None,
                   'SUBJECTS': None,
                   'SOURCE': None,
                   'EXAM_TYPE': None,
                   'PARENT_QUESTION': None,
                   'EXPLANATION': None,
                   'REFERENCE': None,
        }

        try:
            INDEXES['SEQUENCE'] = headers.index('Q#')
        except ValueError:
            pass
        INDEXES['CHOICES'] = [headers.index(header_name)
                              for header_name in headers
                              if header_name.startswith('Choice')]
        try:
            INDEXES['QUESTION_TEXT'] = headers.index('Question')
        except ValueError:
            INDEXES['QUESTION_TEXT'] = headers.index('Question text')

        try:
            INDEXES['ANSWER'] = headers.index('Answer')
        except ValueError:
            try:
                INDEXES['ANSWER'] = headers.index('Right answer')
            except ValueError:
                pass

        INDEXES['SUBJECTS'] = [headers.index(header_name)
                               for header_name in headers
                               if header_name.startswith('Subject')]
        try:
            INDEXES['SOURCE'] = headers.index('Source')
        except ValueError:
            pass
        try:
            INDEXES['EXAM_TYPE'] = headers.index('Exam type')
        except ValueError:
            pass

        INDEXES['ISSUES'] = [headers.index(header_name)
                             for header_name in headers
                             if header_name.startswith('Issue')]
        try:
            INDEXES['PARENT_QUESTION'] = headers.index('Parent question')
        except ValueError:
            try:
                INDEXES['PARENT_QUESTION'] = headers.index('Same case as previous question?')
            except ValueError:
                pass

        try:
            INDEXES['EXPLANATION'] = headers.index('Explanation')
        except ValueError:
            pass

        try:
            INDEXES['REFERENCE'] = headers.index('Reference')
        except ValueError:
            pass

        # The latest question imported is initially None.
        question = None

        for row in csv_reader:
            if INDEXES['SEQUENCE']:
                sequence = int(row[INDEXES['SEQUENCE']])
                print("Handling %d..." % sequence)
                if options['skip_until'] and \
                   options['skip_until'] > sequence:
                    continue
            text = row[INDEXES['QUESTION_TEXT']].strip()
            if not text:
                continue

            choices = []
            for choice_index in INDEXES['CHOICES']:
                choice_text = row[choice_index].strip()
                if choice_text:
                    choice = Choice(text=choice_text)
                    choices.append(choice)

            # Check if the right answer column is filled
            if INDEXES['ANSWER']:
                try:
                    answer = row[INDEXES['ANSWER']].upper()
                    answer_index = ascii_uppercase.index(answer)
                    print("Right answer is %s (%s)"  % (row[INDEXES['ANSWER']], choices[answer_index].text))
                    choices[answer_index].is_right = True
                except (IndexError, ValueError):
                    pass

            subjects = []
            for subject_index in INDEXES['SUBJECTS']:
                question_subject = row[subject_index]
                subject = light_get_from_pool(subject_pool, question_subject)
                if subject:
                    subjects.append(subject)
            if not subjects and default_subject:
                subjects.append(default_subject)

            source = None
            if INDEXES['SOURCE']:
                source = light_get_from_pool(source_pool, row[INDEXES['SOURCE']])

            if not source and default_source:
                source = default_source

            exam_type = None
            if INDEXES['EXAM_TYPE']:
                exam_type = light_get_from_pool(exam_type_pool, row[INDEXES['EXAM_TYPE']])

            if not exam_type and default_exam_type:
                exam_type = default_exam_type

            issues = []
            for issue_index in INDEXES['ISSUES']:
                question_issue = row[issue_index]
                issue = light_get_from_pool(issue_pool, question_issue)
                if issue:
                    issues.append(issue)

            # If parent_question is specified, set it to the the
            # latest imported question.
            if INDEXES['PARENT_QUESTION'] and row[INDEXES['PARENT_QUESTION']] == "Yes":
                parent_question = question
            else:
                parent_question = None

            explanation = ""
            if INDEXES['EXPLANATION']:
                try:
                    explanation = row[INDEXES['EXPLANATION']]
                except IndexError:
                    pass

            reference = ""
            if INDEXES['REFERENCE']:
                try:
                    reference = row[INDEXES['REFERENCE']]
                except IndexError:
                    pass

            if not options['dry']:
                question = Question.objects.create(exam=exam,
                                                   parent_question=parent_question)
                if subjects:
                    question.subjects.add(*subjects)
                question.issues.add(*issues)
                if source:
                    question.sources.add(source)
                if exam_type:
                    question.exam_types.add(exam_type)

                revision = Revision.objects.create(question=question,
                                                   text=text,
                                                   change_summary="Imported from Google Sheets",
                                                   submitter=submitter,
                                                   is_first=True,
                                                   is_last=True)
                if explanation:
                    ExplanationRevision.objects.create(question=question,
                                                       is_first=True,
                                                       is_last=True,
                                                       reference=reference,
                                                       explanation_text=explanation)

                for choice in choices:
                    choice.question = question
                    choice.save()
                revision.choices.add(*choices)
                question.best_revision = revision
                question.save()
                added_pks.append(question.pk)

                
        if not options['is_disapproved']:
            Question.objects.filter(pk__in=added_pks).update(is_approved=True)
            Revision.objects.filter(question_id__in=added_pks).update(is_approved=True)
