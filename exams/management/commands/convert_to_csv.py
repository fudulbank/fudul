from django.core.management.base import BaseCommand
from string import ascii_uppercase
import csv
import sys
import re

regex_patterns = {'PEDIATRIC': {'full_question': ' +\d+\)\s+(?P<question_text>.+\n+(?:.+\n+)*?)(?P<choices>(?: *\(?[a-f][\)\.] .+\n)+)\s*(?:The answer is|Answer|Answer is|The answer|The Correct answer is)\s+\(?(?P<correct_choice>[A-F])\)?\s+\(?\s*(?P<subject>[^\)]+?)\s*\)?\s+(?:Explanation\s*:\s+(?P<explanation>.+\n+(?:.+\n+)*?)?(?= +|END))',
                                'choice': ' *\(?[a-f][\)\.] (.+)\n',
                                'explanation': ''}}

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--raw-file',
                            type=str)
        parser.add_argument('--rule',
                            type=str)
        parser.add_argument('--source',
                            type=str)
        parser.add_argument('--exam-type',
                            type=str)
        parser.add_argument('--answer-csv-file',
                            type=str, default=None)

    def handle(self, *args, **options):
        with open(options['raw_file']) as f:
            raw_text = f.read()

        if options['answer_csv_file']:
            csv_file = open(options['answer_csv_file'])
            csv_reader = csv.reader(csv_file)

        rule = options['rule']
        source = options['source']
        exam_type = options['exam_type']
        automatic_sequence = 1
        csv_writer = csv.writer(sys.stdout)
        csv_writer.writerow(['Sequence', 'Text', 'Choice 1',
                             'Choice 2', 'Choice 3', 'Choice 4',
                             'Choice 5', 'Choice 6', 'Correct choice',
                             'Subject 1', 'Subject 2', 'Subject 3',
                             'Subject 4', 'Source', 'Exam type',
                             'Issue 1', 'Issue 2', 'Parent question',
                             'Explanation', 'Reference'])

        for matched_question in re.finditer(regex_patterns[rule]['full_question'], raw_text, re.M | re.I):
            try:
               sequence = matched_question.group('question_sequence')
            except IndexError:
               sequence = automatic_sequence

            try:
               reference = matched_question.group('reference')
            except IndexError:
               reference = ''

            try:
                correct_choice = matched_question.group('correct_choice')
            except IndexError:
                correct_choice = ''
            subjects = ['', '', '']
            try:
                subjects = [matched_question.group('subject')] + subjects
            except IndexError:
                subjects.append('')
            # We do not support issues
            issues = ['', '']
            question_text = matched_question.group('question_text')
            choices_str = matched_question.group('choices')
            explanation = matched_question.group('explanation')
            choice_list = []
            for choice in re.finditer(regex_patterns[rule]['choice'], choices_str, re.M | re.I):
                choice_text = choice.group(1)
                choice_list.append(choice_text.strip())
            choice_number = len(choice_list)
            if choice_number < 6:
               empty_choices = [''] * (6 - choice_number)
               choice_list += empty_choices
                
            csv_writer.writerow([sequence, question_text] + choice_list + [correct_choice] + subjects + [source, exam_type] + issues + [''] + [explanation, reference])
            automatic_sequence += 1

        if options['answer_csv_file']:
            csv_file.close()
