from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import datetime
import os.path

from exams.models import Answer
from accounts.models import College


current_timezone = timezone.get_current_timezone()

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--initial', dest='is_initial',
                            action='store_true', default=False)

    def get_counts(self, end_date, users):
        # This function is given a day (end_date) and it calculates
        # the activity in the preceding 30 days.

        start_date = end_date - datetime.timedelta(30)
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        aware_start_datetime = timezone.make_aware(start_datetime, current_timezone)

        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        aware_end_datetime = timezone.make_aware(end_datetime, current_timezone)

        user_count = users.filter(session__submission_date__gte=aware_start_datetime,
                                  session__submission_date__lte=aware_end_datetime)\
                          .distinct().count()
        answer_count = Answer.objects.filter(session__submitter__in=users,
                                             session__submission_date__gte=aware_start_datetime,
                                             session__submission_date__lte=aware_end_datetime,
                                             choice__isnull=False)\
                                 .distinct().count()

        return user_count, answer_count

    def calculate_stats(self, end_date, users,
                        user_count, answer_count):
        try:
            answer_avg = answer_count / user_count
        except ZeroDivisionError:
            answer_avg = 0

        yesterday = end_date - datetime.timedelta(1)
        last_user_count, last_answer_count = self.get_counts(yesterday, users)
        try:
            last_answer_avg = last_answer_count / last_user_count
        except ZeroDivisionError:
            last_answer_avg = 0

        if last_user_count != 0:
            user_difference = user_count - last_user_count
            user_change = (user_difference / last_user_count) * 100
        else:
            user_change = 0

        if last_answer_avg != 0:
            answer_difference = answer_avg - last_answer_avg
            answer_change = (answer_difference / last_answer_avg) * 100
        else:
            answer_change = 0

        user_change = "{:0.1f}".format(user_change)
        answer_avg = "{:0.1f}".format(answer_avg)
        answer_change = "{:0.1f}".format(answer_change)

        return [user_change, answer_avg, answer_change]

    def get_stats(self, end_date, users):
        user_count, answer_count = self.get_counts(end_date, users)
        calculated_stats = self.calculate_stats(end_date, users,
                                                user_count,
                                                answer_count)
        return [str(user_count)] + calculated_stats    

    def write_stats(self, end_date, college, csv_file):
        day_str = end_date.strftime('%Y-%m-%d')
        stats = [day_str]

        if college:
            for batch in college.batch_set.all():
                users = User.objects.filter(profile__batch=batch)
                stats += self.get_stats(end_date, users)
        else:
            users = User.objects.all()
            stats += self.get_stats(end_date, users)

        stat_str = ",".join(stats)
        csv_file.write('\n' + stat_str)

    def handle(self, *args, **options):
        user_count = answer_avg = None
        today_date = datetime.date.today()
        colleges = [None] + list(College.objects.all())

        for college in colleges:
            if college:
                csv_filename = 'college-{}.csv'.format(college.pk)
            else:
                csv_filename = 'great-metric.csv'            

            csv_path = os.path.join(settings.STATIC_ROOT, csv_filename)
            if options['is_initial']:
                csv_file = open(csv_path, 'w')
                fields = ['user_count', 'user_change',
                           'answer_avg', 'answer_change']

                headers = ['date']

                if college:
                    for batch in college.batch_set.all():
                        for field in fields:
                           new_field = field + "_" + str(batch.pk)
                           headers.append(new_field)
                else:
                    headers += fields

                header_str = ",".join(headers)
                csv_file.write(header_str)

                # The day the website was lunched
                end_date = datetime.date(2017, 9, 1)

                while today_date > end_date:
                    self.write_stats(end_date, college, csv_file)
                    end_date += datetime.timedelta(1)
            else:
                csv_file = open(csv_path, 'a')

                # This script will run at 00:00 (per website timezone) to
                # get the stats of the previous day.
                end_date = today_date - datetime.timedelta(1)
                self.write_stats(end_date, college, csv_file)

            csv_file.close()
