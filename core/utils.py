from django.db import models
import datetime
import json
import math
import operator

from exams.models import ExamDate


BASIC_SEARCH_FIELDS = ['user__pk', 'user__username', 'user__email',
                       'user__profile__first_name',
                       'user__profile__middle_name',
                       'user__profile__last_name',
                       'user__profile__mobile_number',
                       'user__profile__alternative_email',
                       'user__profile__nickname']

def get_exam_date_json(exam=None):
    pool_exam_dates = ExamDate.objects\
                              .filter(exam__session__isnull=False,
                                      date__gte=datetime.date(2017, 9, 1),
                                      date__lt=datetime.date.today())\
                              .order_by('date')\
                              .distinct()

    if exam:
        pool_exam_dates = pool_exam_dates.filter(exam=exam)

    dates = pool_exam_dates.values_list('date', flat=True)
    exam_dates = {}
    for date in dates:
        date_str = date.strftime('%Y-%m-%d')
        hovertext = []
        for exam_date in pool_exam_dates.filter(date=date):
            hovertext.append('<b>{}</b><br>{}'.format(exam_date.name, str(exam_date.batch)))
        hovertext_str = '<span style=\\"font-weight: 700; text-decoration: underline;\\">{}:</span><br>'.format(date.strftime('%h %d')) + \
                        '<br>'.join(hovertext)
        exam_dates[date_str] = hovertext_str
    exam_date_json = json.dumps(exam_dates)

    return exam_date_json

def get_search_queryset(queryset, search_fields, search_term):
    # Based on the Django app search functionality found in the
    # function get_search_results of django/contrib/admin/options.py.
    if search_term:
        orm_lookups = [search_field + '__icontains'
                       for search_field in search_fields]
        for bit in search_term.split():
            or_queries = [models.Q(**{orm_lookup: bit})
                          for orm_lookup in orm_lookups]
            statement = models.Q()
            for or_query in or_queries:
                statement = operator.or_(or_query, statement)
            queryset = queryset.filter(statement)

    return queryset

def round_to(number, cut_off):
    return math.floor(number / cut_off) * cut_off
