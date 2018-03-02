from difflib import SequenceMatcher
from django.core.management.base import BaseCommand
from exams.models import Exam, Revision, Duplicate
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
        for exam in Exam.objects.all():
            if options['verbose']:
                print("Scanning {}...".format(exam.name))
            pool = list(Revision.objects.filter(best_of__isnull=False,
                                                question__is_deleted=False,
                                                question__exam=exam)\
                                        .order_by('pk'))

            # We keep a list of revisions that have already been found to
            # be duplicate so we do not re-scan them.
            found = []
            for first_revision in pool:
                # If the revision has been reported to be a duplicate,
                # skip it.
                if first_revision.pk in found:
                    continue
                if options['verbose']:
                    start_time = datetime.datetime.now()
                for second_revision in pool:
                    # Do not compare the revision to itself.
                    if first_revision.pk == second_revision.pk:
                        continue

                    matcher = SequenceMatcher(None, first_revision.text,
                                              second_revision.text)
                    ratio = matcher.ratio()

                    # If the revision is too short, we use a higher
                    # cutt off.
                    is_short = len(first_revision.text) <= options['short_limit']
                    if is_short and ratio >= 0.90 or \
                       not is_short and ratio >= options['cutoff']:
                        found.append(second_revision.pk)
                        if not options['dry']:
                            # If a duplication report is already
                            # pending for the first revision, do not
                            # create a new one until it is solved.
                            if Duplicate.objects.filter(first_revision=first_revision,
                                                        status="PENDING")\
                                                .exclude(second_revision=second_revision)\
                                                .exists() or \
                               Duplicate.objects.filter(first_revision=second_revision,
                                                        status="PENDING")\
                                                .exists():
                                continue
                            Duplicate.objects.get_or_create(first_revision=first_revision,
                                                            second_revision=second_revision,
                                                            defaults={'ratio':ratio})
                        if options['verbose']:
                            print("1st:", first_revision.text)
                            print("2nd:", second_revision.text)
                            print(first_revision.pk, second_revision.pk, ratio)            
                if options['verbose']:
                    end_time = datetime.datetime.now()
                    print("Revision #{} took: {}".format(first_revision.pk, end_time - start_time))
