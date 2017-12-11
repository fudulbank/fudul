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

    def get_counts(self, end_date, users, exam=None):
        # This function is given a day (end_date) and it calculates
        # the activity in the preceding 30 days.

        start_date = end_date - datetime.timedelta(30)
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        aware_start_datetime = timezone.make_aware(start_datetime, current_timezone)

        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        aware_end_datetime = timezone.make_aware(end_datetime, current_timezone)

        kwargs = {'session__submission_date__gte': aware_start_datetime,
                  'session__submission_date__lte': aware_end_datetime}

        if exam:
            kwargs['session__exam'] = exam
        user_count = users.filter(**kwargs)\
                          .distinct().count()

        kwargs = {'session__submitter__in': users,
                  'session__submission_date__gte': aware_start_datetime,
                  'session__submission_date__lte': aware_end_datetime,
                  'choice__isnull': False}
        if exam:
            kwargs['session__exam'] = exam
        answer_count = Answer.objects.filter(**kwargs)\
                                 .distinct().count()
        try:
            answer_avg = answer_count / user_count
        except ZeroDivisionError:
            answer_avg = 0
        answer_avg = "{:0.1f}".format(answer_avg)

        return str(user_count), answer_avg

    def write_stats(self, end_date, target, csv_file):
        day_str = end_date.strftime('%Y-%m-%d')
        stats = [day_str]

        if type(target) is College:
            for batch in target.batch_set.all():
                users = User.objects.filter(profile__batch=batch)
                stats += self.get_counts(end_date, users)
        if type(target) is Exam:
            users = User.objects.all()
            stats += self.get_counts(end_date, users, exam=target)
        else:
            users = User.objects.all()
            stats += self.get_counts(end_date, users)

        stat_str = ",".join(stats)
        csv_file.write(stat_str + '\n')

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
