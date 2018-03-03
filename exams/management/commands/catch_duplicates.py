from difflib import SequenceMatcher
from django.core.management.base import BaseCommand
from exams.models import Exam, Question, Duplicate, DuplicateContainer
import datetime


class Command(BaseCommand):
    help = "Clean-up tasks for the exam app"
    def add_arguments(self, parser):
        parser.add_argument('--verbose', action='store_true',
                            default=False)
        parser.add_argument('--dry', action='store_true',
                            default=False)
        parser.add_argument('--cutoff', default=0.85,
                            type=float)
        parser.add_argument('--short-limit', default=70,
                            type=int)

    def handle(self, *args, **options):
        for exam in Exam.objects.order_by('pk'):
            if options['verbose']:
                print("Scanning {}...".format(exam.name))
            pool = list(Question.objects.select_related('best_revision')\
                                        .filter(exam=exam,
                                                best_revision__isnull=False)\
                                        .undeleted()\
                                        .order_by('pk'))

            # We keep a list of revisions that have already been found to
            # be duplicate so we do not re-scan them.
            found = []
            for first_question in pool:
                duplicates = []
                # If the revision has been reported to be a duplicate,
                # skip it.
                if first_question.pk in found:
                    continue
                if options['verbose']:
                    start_time = datetime.datetime.now()
                for second_question in pool:
                    # As a general rule: the duplicate container
                    # primary question is always the question with the
                    # smaller primary key.  If the primary key of the
                    # first question is higher than that of the second
                    # question, skip the scan, as it must have been
                    # done before.
                    if first_question.pk >= second_question.pk:
                        continue

                    matcher = SequenceMatcher(None, first_question.best_revision.text,
                                              second_question.best_revision.text)
                    ratio = matcher.ratio()

                    # If the revision is too short, we use a higher
                    # cutt off.
                    is_short = len(first_question.best_revision.text) <= options['short_limit']

                    if is_short and ratio >= 0.90 or \
                       not is_short and ratio >= options['cutoff']:
                        found.append(second_question.pk)
                        duplicates.append((second_question, ratio))
                        if options['verbose']:
                            print("1st:", first_question.best_revision.text)
                            print("2nd:", second_question.best_revision.text)
                            print(second_question.pk, second_question.pk, ratio)
                if not options['dry'] and duplicates:
                    # If an identical previous container has been
                    # declined, do not re-create it.
                    declined_container = DuplicateContainer.objects.filter(primary_question=first_question,
                                                                           status="DECLINED")
                    for question, ratio in duplicates:
                        declined_container = declined_container.filter(duplicate__question=question)
                    if declined_container.exists():
                        print("Question #{}: An identical previous container was declined. Skip this one.".format(first_question.pk))
                        continue

                    # If a previous container is pending, get it, so
                    # we can add to it,
                    container, was_created = DuplicateContainer.objects.get_or_create(
                        status="PENDING",
                        primary_question=first_question)
                    for question, ratio in duplicates:
                        Duplicate.objects.get_or_create(container=container,
                                                        question=question,
                                                        defaults={'ratio':ratio})
                if options['verbose']:
                    end_time = datetime.datetime.now()
                    print("Question #{}: It took: {}".format(first_question.pk, end_time - start_time))
