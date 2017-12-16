from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.db.models import Count, F
from django.utils import timezone
import datetime

from notifications.signals import notify
from exams.models import Session


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Notify users abouts sessions that have been pending for 48 hours.
        target_date = timezone.now() - datetime.timedelta(2)
        pending_sessions = Session.objects.select_related('exam', 'exam__category')\
                                          .undeleted()\
                                          .with_accessible_questions()\
                                          .filter(submission_date__lte=target_date)\
                                          .annotate(question_number=Count('questions'),
                                                    answer_number=Count('answer'))\
                                          .filter(question_number__gt=F('answer_number'))\
                                          .exclude(notifications__verb='is still pending',
                                                   session_mode__in=['INCOMPLETE', 'SOLVED'])
        for session in pending_sessions:
            url = reverse("exams:show_session",
                          args=(session.exam.category.get_slugs(),
                                session.exam.pk,
                                session.pk))
            notify.send(session, recipient=session.submitter, verb='is still pending',
                        timestamp=session.submission_date, url=url)
        
