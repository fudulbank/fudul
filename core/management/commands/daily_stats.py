from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import datetime
import os.path

from exams.models import Exam, Answer
from accounts.models import College


current_timezone = timezone.get_current_timezone()

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--initial', dest='is_initial',
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
        answer_avg = "{:0.1f}".format(answer_avg)

        return user_count, answer_avg

    def get_contribution_counts(self, users=None, exam=None):
        explanation_kwargs = {'submitted_explanations__submission_date__gte': self.aware_start_datetime,
                              'submitted_explanations__submission_date__lte': self.aware_end_datetime}
        revision_kwargs = {'revision__submission_date__gte': self.aware_start_datetime,
                           'revision__submission_date__lte': self.aware_end_datetime}

        if exam:
            revision_kwargs['revision__question__exam'] = exam
            explanation_kwargs['submitted_explanations__question__exam'] = exam

        if users:
            target_users = users
        else:
            target_users = User.objects.all()

        explainer_count = target_users.filter(**explanation_kwargs)\
                                      .distinct().count()
        editor_count = users.filter(**revision_kwargs)\
                            .distinct().count()

        return explainer_count, editor_count

    def write_stats(self, end_date, target, csv_file):
        self.set_dates(end_date)
        day_str = end_date.strftime('%Y-%m-%d')
        stats = [day_str]

        if type(target) is College:
            for batch in target.batch_set.all():
                users = User.objects.filter(profile__batch=batch)
                user_count, answer_avg = self.get_usage_counts(users)
                explainer_count, editor_count = self.get_contribution_counts(users)
        if type(target) is Exam:
            user_count, answer_avg = self.get_usage_counts(exam=target)
            explainer_count, editor_count = self.get_contribution_counts(exam=target)
        else:
            user_count, answer_avg = self.get_usage_counts()
            explainer_count, editor_count = self.get_contribution_counts()

        stats += [user_count, answer_avg, explainer_count,
                  editor_count]

        stat_str = [str(stat) for stat in stats]
        row = ",".join(stat_str)
        csv_file.write(row + '\n')

    def handle(self, *args, **options):
        user_count = answer_avg = None
        today_date = datetime.date.today()
        exams = Exam.objects.filter(session__isnull=False).distinct()
        colleges = College.objects.filter(profile__isnull=False).distinct()
        targets = [None] + list(colleges)\
                         + list(exams)

        for target in targets:
            if type(target) is Exam:
                csv_filename = 'exam-{}.csv'.format(target.pk)
            elif type(target) is College:
                csv_filename = 'college-{}.csv'.format(target.pk)
            else:
                csv_filename = 'great-metric.csv'            

            csv_path = os.path.join(settings.STATIC_ROOT, csv_filename)
            if options['is_initial']:
                csv_file = open(csv_path, 'w')
                fields = ['user_count', 'answer_avg']

                headers = ['date']

                if type(target) is College:
                    for batch in target.batch_set.all():
                        for field in fields:
                           new_field = field + "_" + str(batch.pk)
                           headers.append(new_field)
                else:
                    headers += fields

                header_str = ",".join(headers)
                csv_file.write(header_str + '\n')

                # The day the website was lunched
                end_date = datetime.date(2017, 9, 1)

                while today_date > end_date:
                    self.write_stats(end_date, target, csv_file)
                    end_date += datetime.timedelta(1)
            else:
                csv_file = open(csv_path, 'a')

                # This script will run at 00:00 (per website timezone) to
                # get the stats of the previous day.
                end_date = today_date - datetime.timedelta(1)
                self.write_stats(end_date, target, csv_file)

            csv_file.close()
