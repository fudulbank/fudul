from difflib import SequenceMatcher
from django.core.management.base import BaseCommand
from django.db.models import Count
from exams.models import *
import datetime
import time

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
        parser.add_argument('--fast', action='store_true',
                            default=False)
        parser.add_argument('--exam-pk', default=None, type=int)

    def handle(self, *args, **options):
        if not options['fast']:
            question_count = Question.objects.undeleted().count()
            # Run over 20 hours
            total_seconds = 60 * 60 * 20
            sleep_time = question_count / total_seconds

        # Clean up duplicate containers with no undeleted questions
        obsolete_containers =  DuplicateContainer.objects.filter(status='PENDING')\
                                                         .exclude(duplicate__question__is_deleted=False,
                                                                  duplicate__question__revision__is_deleted=False) | \
                               DuplicateContainer.objects.filter(status='PENDING')\
                                                         .exclude(primary_question__is_deleted=False,
                                                                  primary_question__revision__is_deleted=False)

        if options['verbose']:
            print("Found {} obsolute containers.  Deleting...".format(obsolete_containers.count()))
        obsolete_containers.delete()

        if options['exam_pk']:
            exams = Exam.objects.filter(pk=options['exam_pk'])
        else:
            exams = Exam.objects.order_by('pk')

        for exam in exams:
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
                if not options['fast']:
                    if options['verbose']:
                        print("Sleeping for {}...".format(sleep_time))
                    time.sleep(sleep_time)

        # Some duplicates can be solved automatically: if the ratio is
        # 100% and the question pks are subsequent, this indicates
        # that the duplication is the result of a double creation
        # click.  We can keep the primary question and remoe others.
        for container in DuplicateContainer.objects.select_related('primary_question',
                                                                   'primary_question__best_revision')\
                                           .filter(status="PENDING",
                                                   duplicate__ratio=1)\
                                           .exclude(duplicate__ratio__lt=1)\
                                           .order_by('primary_question')\
                                           .distinct():
            consistant = False
            expected_pk = container.primary_question.pk + 1
            question_ids = container.duplicate_set.values_list('question', flat=True)\
                                                  .order_by('question')
            for question_id in question_ids:
                if expected_pk == question_id:
                    consistant = True
                    expected_pk += 1
                else:
                    consistant = False
                    break
            if consistant:
                if options['verbose']:
                    question_id_str = ", ".join(question_ids)
                    print("Keeping {}, and deleting {}...".format(container.primary_question.pk, question_id_str))
                container.keep(container.primary_question)
                container.status = 'KEPT'
                container.save()
