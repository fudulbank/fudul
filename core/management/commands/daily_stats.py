from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.conf import settings
import datetime
import os.path

from exams.models import *
from accounts.models import College


current_timezone = timezone.get_current_timezone()

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--initial', dest='is_initial',
                            action='store_true', default=False)
        parser.add_argument('--dry', dest='is_dry',
                            action='store_true', default=False)

    def set_dates(self, end_date):
        # This function is given a day (end_date) and it calculates
        # the activity in the preceding 30 days.

        start_date = end_date - datetime.timedelta(30)
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        self.aware_start_datetime = timezone.make_aware(start_datetime, current_timezone)

        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        self.aware_end_datetime = timezone.make_aware(end_datetime, current_timezone)

    def get_usage_counts(self, users=None, exam=None):
        # Shared query parameters
        kwargs = {'session__submission_date__gte': self.aware_start_datetime,
                  'session__submission_date__lte': self.aware_end_datetime}
        if exam:
            kwargs['session__exam'] = exam

        # Calculate active users
        if users:
            target_users = users
        else:
            target_users = User.objects.all()
        user_count = target_users.filter(**kwargs)\
                                 .distinct().count()

        # Calculate average answers

        # Exclude skipped answers (i.e. those without a choice)
        kwargs['choice__isnull'] = False
        if users:
            kwargs['session__submitter__in'] = users

        answer_count = Answer.objects.filter(**kwargs)\
                                     .distinct().count()
        try:
            answer_avg = answer_count / user_count
        except ZeroDivisionError:
            answer_avg = 0

        return [user_count, answer_avg]

    def get_contribution_counts(self, users=None, exam=None):
        editor_kwargs = {}
        explainer_kwargs = {}
        mnemonicer_kwargs = {}

        basic_kwargs = {'submission_date__gte': self.aware_start_datetime,
                        'submission_date__lte': self.aware_end_datetime,
                        'is_deleted': False}

        if users:
            target_users = users
            basic_kwargs['submitter__in'] = users
        else:
            target_users = User.objects.all()
        if exam:
            basic_kwargs['question__exam'] = exam

        mnemonic_kwargs = basic_kwargs.copy()
        explanation_kwargs = basic_kwargs.copy()
        explanation_kwargs['is_contribution'] = True
        revision_kwargs = basic_kwargs.copy()
        revision_kwargs['is_contribution'] = True

        # Answer does not have 'is_deleted' and 'question' fields
        correction_kwargs = basic_kwargs.copy()
        del correction_kwargs['is_deleted']
        if 'question__exam' in correction_kwargs:
            del correction_kwargs['question__exam']

        revision_qs = Revision.objects.filter(**revision_kwargs)
        explanation_qs = ExplanationRevision.objects.filter(**explanation_kwargs)
        correction_qs = AnswerCorrection.objects.filter(**correction_kwargs)
        mnemonic_qs = Mnemonic.objects.filter(**mnemonic_kwargs)

        # Using .union() with .values() is a vary efficient way to
        # calculate contributor number.
        contributor_count = revision_qs.values('submitter').union(correction_qs.values('submitter'),
                                                                  explanation_qs.values('submitter'),
                                                                  mnemonic_qs.values('submitter'))\
                                                           .count()

        revision_count = revision_qs.distinct().count()
        explanation_count = explanation_qs.distinct().count()
        correction_count = correction_qs.distinct().count()
        mnemonic_count = mnemonic_qs.distinct().count()

        return [contributor_count, revision_count, explanation_count,
                correction_count, mnemonic_count]

    def write_stats(self, end_date, target, csv_file):
        self.set_dates(end_date)
        day_str = end_date.strftime('%Y-%m-%d')
        stats = [day_str]

        if type(target) is College:
            for batch in target.batch_set.all():
                users = User.objects.filter(profile__batch=batch)
                stats += self.get_usage_counts(users)
                stats += self.get_contribution_counts(users)
        elif type(target) is Exam:
            stats += self.get_usage_counts(exam=target)
            stats += self.get_contribution_counts(exam=target)
        else:
            stats += self.get_usage_counts()
            stats += self.get_contribution_counts()

        stat_str = []
        for stat in stats:
            if type(stat) is float:
                stat = "{:0.1f}".format(stat)
            else:
                stat = str(stat)
            stat_str.append(stat)

        row = ",".join(stat_str)
        if csv_file:
            csv_file.write(row + '\n')
        else:
            print(self.header_str)
            print(row)

    def handle(self, *args, **options):
        is_dry = options['is_dry']
        user_count = answer_avg = None
        today_date = datetime.date.today()
        exams = Exam.objects.filter(session__isnull=False)\
                            .order_by('pk')\
                            .distinct()
        colleges = College.objects.filter(profile__isnull=False)\
                                  .order_by('pk')\
                                  .distinct()
        targets = [None] + list(colleges)\
                         + list(exams)

        for target in targets:
            if type(target) is Exam:
                csv_filename = 'exam-{}.csv'.format(target.pk)
            elif type(target) is College:
                csv_filename = 'college-{}.csv'.format(target.pk)
            else:
                csv_filename = 'great-metric.csv'            

            fields = ['user_count', 'answer_avg', 'contributor_count',
                      'revision_count', 'explanation_count',
                      'correction_count', 'mnemonic_count']

            headers = ['date']

            if type(target) is College:
                for batch in target.batch_set.all():
                    for field in fields:
                       new_field = field + "_" + str(batch.pk)
                       headers.append(new_field)
            else:
                headers += fields

            self.header_str = ",".join(headers)

            csv_path = os.path.join(settings.PRIVILEGED_DIR, 'indicators', csv_filename)
            if options['is_initial']:
                if not is_dry:
                    csv_file = open(csv_path, 'w')
                    csv_file.write(self.header_str + '\n')
                else:
                    csv_file = None

                # The day the website was lunched
                end_date = datetime.date(2017, 9, 1)

                while today_date > end_date:
                    self.write_stats(end_date, target, csv_file)
                    end_date += datetime.timedelta(1)
            else:
                if not is_dry:
                    csv_file = open(csv_path, 'a')
                else:
                    csv_file = None

                # This script will run at 00:00 (per website timezone) to
                # get the stats of the previous day.
                end_date = today_date - datetime.timedelta(1)
                self.write_stats(end_date, target, csv_file)

            if not is_dry:
                csv_file.close()
