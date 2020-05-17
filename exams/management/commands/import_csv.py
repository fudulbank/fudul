from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand
from string import ascii_uppercase
import csv
import os
import urllib.parse

from exams.models import *


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
        parser.add_argument('--exam-pk', type=int, required=True)
        parser.add_argument('--question-csv', required=True)

        parser.add_argument('--default-exam-type', default=None)
        parser.add_argument('--default-source', default=None)
        parser.add_argument('--default-subject', default=None)
        parser.add_argument('--disapproved', dest='is_disapproved',
                            action='store_true', default=False)
        parser.add_argument('--dry', action='store_true',
                            default=False)
        parser.add_argument('--figure-csv')
        parser.add_argument('--figure-root')

        parser.add_argument('--skip-until', default=None)
        parser.add_argument('--submitter-email', default=None)

    def handle(self, *args, **options):
        csv_file = open(options['question_csv'])
        question_reader = csv.reader(csv_file)
        exam = Exam.objects.get(pk=options['exam_pk'])
        subject_pool = exam.subject_set.all()
        exam_type_pool = exam.exam_types.all()
        source_pool = exam.get_sources()
        issue_pool = Issue.objects.all()
        added_pks = []

        if options['figure_csv']:
            figures = {}
            with open(options['figure_csv']) as f:
                figure_reader = csv.reader(f)
                next(figure_reader)
                for row in figure_reader:
                    # Skip non-integer question_ids
                    sequence = row[2]
                    try:
                        if type(sequence) is str:
                            sequence = sequence.strip()
                        sequence = int(sequence)
                    except ValueError:
                        continue

                    path = urllib.parse.unquote(row[1])
                    figure_place = row[3].strip()

                    assert figure_place in ['Question', 'Explanation']

                    try:
                        caption = row[4]
                    except IndexError:
                        caption = ""

                    if not sequence in figures:
                        figures[sequence] = []
                    
                    data = {'path': path,
                            'figure_place': figure_place,
                            'caption': caption}
                    figures[sequence].append(data)

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

        headers = next(question_reader)

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
            try:
                INDEXES['SEQUENCE'] = headers.index('Sequence')
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

        for row in question_reader:
            if not INDEXES['SEQUENCE'] is None:
                sequence = int(row[INDEXES['SEQUENCE']])
                print("Handling %d..." % sequence)
                if options['skip_until'] and \
                   options['skip_until'] > sequence:
                    continue
            else:
                print("No sequence was provided!")
                raise Exception()
                    
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

            explanation_text = ""
            if INDEXES['EXPLANATION']:
                try:
                    explanation_text = row[INDEXES['EXPLANATION']]
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
                if explanation_text:
                    explanation = ExplanationRevision.objects\
                                                     .create(question=question,
                                                             is_first=True,
                                                             is_last=True,
                                                             reference=reference,
                                                             explanation_text=explanation_text)

                for choice in choices:
                    choice.question = question
                    choice.save()
                revision.choices.add(*choices)
                question.best_revision = revision
                question.save()
                print("sequence", sequence)

                if options['figure_csv'] and sequence in figures:
                    figure_count = 1
                    question_figures = []
                    explanation_figures = []
                    for figure_data in figures[sequence]:
                        clean_path = os.path.join(options['figure_root'],
                                                  urllib.parse.unquote(figure_data['path']))
                        figure = Figure.objects.create(caption=figure_data['caption'])
                        extension = clean_path.split('.')[-1]
                        print(f"Adding the figure in `{clean_path}` to question #{sequence} ({figure_data['figure_place']})...")
                        with open(clean_path, 'rb') as figure_file:
                            print(f'prep-{sequence}-{figure_count}.{extension}')
                            figure.figure.save(f'prep-{sequence}-{figure_count}.{extension}',
                                               File(figure_file))
                        figure_count += 1
                        if figure_data['figure_place'] == 'Question':
                            question_figures.append(figure)
                        elif figure_data['figure_place'] == 'Explanation':
                            explanation_figures.append(figure)
                    if question_figures:
                        revision.figures.add(*question_figures)
                    if explanation_figures:
                        explanation.figures.add(*explanation_figures)

                added_pks.append(question.pk)
                
        if not options['is_disapproved']:
            Question.objects.filter(pk__in=added_pks).update(is_approved=True)
            Revision.objects.filter(question_id__in=added_pks).update(is_approved=True)
