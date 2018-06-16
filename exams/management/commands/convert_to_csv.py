from django.core.management.base import BaseCommand
from string import ascii_uppercase
import csv
import sys
import re

regex_patterns = {'PEDIATRIC_PART_I': {'full_question': ' +\d+[\.\-\)]\s+(?P<question_text>.+\n+(?:.+\n+)*?)(?P<choices>(?: *\(?[a-f][\-\)\.] .+\n)+)\s*(?:The answer is|Answer|Answer is|The answer|The Correct answer is)\s+\(?(?P<answer>[A-F])\)?\s+\(?\s*(?P<subject>[^\)]+?)\s*\)?\s+(?:Explanation\s*:?\s+(?P<explanation>.+\n+(?:.+\n+)*?)?(?= +|END))',
                                'choice': ' *\(?[a-f][\)\.] (.+)\n',
                                'explanation': ''},
                  'PEDIATRIC_PROMOTION': {'full_question': '^(?P<question_sequence>\d+)\.\s*(?P<question_text>.+(\n.+)*?)\n(?P<choices>(?: *\(?[a-f][\-\)\.] .+\n)+)\s*',
                                          'choice': ' *\(?[a-f][\)\-\.] (.+)\n'},
                  'PEDIATRIC_ARAB_BOARD': {'full_question': '^(?P<question_sequence>\d+)\.\s+(?P<question_text>.+\n+(?:.+\n+)*?)(?P<choices>(?: *\(?[a-f][\-\)\.] .+\n)+)',
                                'choice': ' *\(?[a-f][\)\-\.] (.+)\n'},
                  'TAIF': {'full_question': '^(?P<question_sequence>\d+)\.\s*(?P<question_text>.+\n+(?:.+\n+)*?)(?P<choices>(?:^ *\(?[a-f][\-\)\.,] *.+\n)+)\s*The answer is\s+(?P<answer>[A-F])',
                                'choice': '^ *\(?[a-f][\)\-\.] *(.+)\n'},
                  'PNU': {'full_question': '^ *(?P<question_sequence>\d+)\.\s*(?P<question_text>.+\n+(?:.+\n+)*?)(?P<choices>(?: *\(?[a-f][\-\)\.] *.+\n)+)\s*?(?:Answer is\s+(?P<answer>[A-F]))?\s+?',
                                'choice': ' *\(?[a-f][\)\-\.] *(.+)\n'},
}

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--raw-file',
                            type=str)
        parser.add_argument('--rule',
                            type=str)
        parser.add_argument('--source',
                            type=str)
        parser.add_argument('--remove-line-breaks',
                            action='store_true')
        parser.add_argument('--exam-type',
                            type=str)
        parser.add_argument('--answer-csv-file',
                            type=str, default=None)

    def handle(self, *args, **options):
        with open(options['raw_file']) as f:
            raw_text = f.read()

        if options['answer_csv_file']:
            answers = {}
            explanations = {}
            with open(options['answer_csv_file']) as f:
                csv_reader = csv.reader(f)
                for row in csv_reader:
                    # Escape empty rows
                    if not len(row):
                        continue
                    sequence = row[0]
                    answer = row[1]
                    answers[sequence] = answer.upper()
                    try:
                        explanation = row[2]
                    except IndexError:
                        pass
                    else:
                        explanations[sequence] = explanation

        rule = options['rule']
        source = options['source']
        exam_type = options['exam_type']
        automatic_sequence = 1
        csv_writer = csv.writer(sys.stdout)
        csv_writer.writerow(['Sequence', 'Text', 'Choice 1',
                             'Choice 2', 'Choice 3', 'Choice 4',
                             'Choice 5', 'Choice 6', 'Answer',
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
            if options['answer_csv_file']:
                answer = answers.get(sequence, '')
                explanation = explanations.get(sequence, '')
            else:
                try:
                    answer = matched_question.group('answer')
                except IndexError:
                    answer = ''
                try:
                    explanation = matched_question.group('explanation').strip()
                except IndexError:
                    explanation = ''
            subjects = ['', '', '']
            try:
                subjects = [matched_question.group('subject')] + subjects
            except IndexError:
                subjects.append('')
            # We do not support issues
            issues = ['', '']
            question_text = matched_question.group('question_text').strip()
            if options['remove_line_breaks']:
                question_text = question_text.replace('\n', ' ')
                question_text = question_text.replace('  ', ' ')
            choices_str = matched_question.group('choices')
            choice_list = []
            for choice in re.finditer(regex_patterns[rule]['choice'], choices_str, re.M | re.I):
                choice_text = choice.group(1)
                choice_list.append(choice_text.strip())
            choice_number = len(choice_list)
            if choice_number < 6:
               empty_choices = [''] * (6 - choice_number)
               choice_list += empty_choices
                
            csv_writer.writerow([sequence, question_text] + choice_list + [answer] + subjects + [source, exam_type] + issues + [''] + [explanation, reference])
            automatic_sequence += 1
