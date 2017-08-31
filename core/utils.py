from django.db import models
import operator

BASIC_SEARCH_FIELDS = ['user__pk', 'user__username', 'user__email',
                       'user__profile__first_name',
                       'user__profile__middle_name',
                       'user__profile__last_name',
                       'user__profile__mobile_number',
                       'user__profile__alternative_email',
                       'user__profile__nickname']

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
