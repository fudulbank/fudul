from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.db.models import Count, F
from django.utils import timezone
import datetime

from notifications.signals import notify
from exams.models import *


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--dry', dest='is_dry',
                            action='store_true', default=False)

    def handle(self, *args, **options):
        # Notify users abouts sessions that have been pending for 48 hours.
        target_date = timezone.now() - datetime.timedelta(2)
        pending_sessions = Session.objects.select_related('exam', 'exam__category')\
                                          .undeleted()\
                                          .filter(submission_date__lte=target_date,
                                                  submitter__isnull=False,
                                                  has_finished=False)\
                                          .exclude(actor_notifications__verb='is still pending')\
                                          .exclude(session_mode__in=['INCOMPLETE', 'SOLVED'])
        for session in pending_sessions:
            url = session.get_absolute_url()
            if not options['is_dry']:
                notify.send(session, recipient=session.submitter,
                            verb='is still pending',
                            timestamp=session.submission_date,
                            url=url)
            else:
                print("Notification for {}".format(str(session)))

        # Notify users who contribute explanations, mnemonics, edits
        # and corrections when there explanations are viewed at 100,
        # 500 and 1,000s.
        thresholds = [100, 500] + [i * 1000 for i in range(1, 10)]

        for threshold in thresholds:
            verb = "got {} views".format(threshold)
            explanations = ExplanationRevision.objects.select_related('question',
                                                                      'question__exam')\
                                                      .undeleted()\
                                                      .filter(submitter__isnull=False,
                                                              question__answer__submission_date__gte=F("submission_date"))\
                                                      .annotate(answer_count=Count('question__answer'))\
                                                      .filter(answer_count__gte=threshold)\
                                                      .exclude(actor_notifications__verb=verb)
            for explanation in explanations:
                title = "Your explanation was seen more than {} times!".format(threshold)
                description = "Your explanation to question #{} in {} was seen {} times.".format(explanation.question.pk,
                                                                                                 explanation.question.exam.name,
                                                                                                 explanation.answer_count)
                url = explanation.get_absolute_url()
                if not options['is_dry']:
                    notify.send(explanation,
                                recipient=explanation.submitter,
                                verb=verb, title=title,
                                description=description, url=url,
                                style='count')
                else:
                    print("Notification for {}".format(str(explanation)))

            revisions = Revision.objects.select_related('question',
                                                        'question__exam')\
                                        .undeleted()\
                                        .filter(is_approved=True,
                                                submitter__isnull=False,
                                                question__answer__submission_date__gte=F("submission_date"))\
                                        .annotate(answer_count=Count('question__answer'))\
                                        .filter(answer_count__gte=threshold)\
                                        .exclude(actor_notifications__verb=verb)

            for revision in revisions:
                title = "Your edit was seen more than {} times!".format(threshold)
                description = "Your edit to question #{} in {} was seen {} times.".format(revision.question.pk,
                                                                                          revision.question.exam.name,
                                                                                          revision.answer_count)
                url = revision.get_absolute_url()
                if not options['is_dry']:
                    notify.send(revision,
                                recipient=revision.submitter,
                                verb=verb, title=title,
                                description=description, url=url,
                                style='count')
                else:
                    print("Notification for {}".format(str(revision)))

            mnemonics = Mnemonic.objects.select_related('question',
                                                        'question__exam')\
                                        .filter(is_deleted=False,
                                                submitter__isnull=False,
                                                question__answer__submission_date__gte=F("submission_date"))\
                                        .annotate(answer_count=Count('question__answer'))\
                                        .filter(answer_count__gte=threshold)\
                                        .exclude(actor_notifications__verb=verb)\
                                        .distinct()

            for mnemonic in mnemonics:
                title = "Your mnemonic was seen more than {} times!".format(threshold)
                description = "Your mnemonic to question #{} in {} was seen {} times.".format(mnemonic.question.pk,
                                                                                              mnemonic.question.exam.name,
                                                                                              mnemonic.answer_count)
                if not options['is_dry']:
                    notify.send(mnemonic,
                                recipient=mnemonic.submitter,
                                verb=verb, title=title,
                                description=description, url=url,
                                style='count')
                else:
                    print("Notification for {}".format(str(mnemonic)))


            corrections = AnswerCorrection.objects.select_related('choice',
                                                          'choice__revision',
                                                          'choice__revision__question',
                                                          'choice__revision__question__exam')\
                                          .filter(submitter__isnull=False,
                                                  choice__revision__question__is_deleted=False,
                                                  choice__revision__question__answer__submission_date__gte=F("submission_date"))\
                                          .annotate(answer_count=Count('choice__revision__question__answer'))\
                                          .filter(answer_count__gte=threshold)\
                                          .exclude(actor_notifications__verb=verb)\
                                          .distinct()

            for correction in corrections:
                title = "Your correction was seen more than {} times!".format(threshold)
                description = "Your correction to question #{} in {} was seen {} times.".format(correction.choice.revision.question.pk,
                                                                                                correction.choice.revision.question.exam.name,
                                                                                                correction.answer_count)
                if not options['is_dry']:
                    notify.send(correction,
                                recipient=correction.submitter,
                                verb=verb, title=title,
                                description=description,
                                style='count')
                else:
                    print("Notification for {}".format(str(correction)))
