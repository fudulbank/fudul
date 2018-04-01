from dal import autocomplete
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators import csrf
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST, require_safe
from django.views.static import serve

from . import decorators, utils
from .models import CoreMember
from exams.models import *
from teams.models import Team
from accounts.models import College
import accounts.utils
import teams.utils


@require_safe
def show_index(request):
    if request.user.is_authenticated():

        latest_sessions = request.user.session_set.select_related('exam',
                                                                  'exam__category')\
                                                  .undeleted()\
                                                  .order_by('-pk')[:8]
        context = {'latest_sessions': latest_sessions}
        if teams.utils.is_editor(request.user):
            revision_pool = Revision.objects.undeleted()\
                                            .filter(submitter=request.user)
            added_question_count = revision_pool.filter(is_first=True).count()
            context['added_question_count'] = added_question_count
            edited_question_count = revision_pool.exclude(is_first=True).count()
            context['edited_question_count'] = edited_question_count
        return render(request, 'index.html', context)

    else:
        # To maximize speed, we use the 'update_cache' management
        # command to update the variables.  To make sure that we are
        # updating the cached variables before they are requested
        # while expired, we add 60 seconds to the view's cache.
        return cache_page(settings.CACHE_PERIODS['DYNAMIC'])(show_index_unauthenticated)(request)

def show_index_unauthenticated(request):
    cached_values = cache.get_many(['sample_question',
                                    'question_count', 'answer_count',
                                    'correct_percentage'])

    sample_question = cached_values.get('sample_question',
                                        Question.objects.first())
    question_count = cached_values.get('question_count', 0)
    answer_count = cached_values.get('answer_count',
                                     Answer.objects.filter(choice__isnull=False).count())
    correct_percentage = cached_values.get('correct_percentage', 0)

    context = {'question_count': question_count,
               'answer_count': answer_count,
               'question': sample_question,
               'correct_percentage': correct_percentage}
    return render(request, 'index_unauthenticated_smle.html', context)

class UserAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return User.objects.none()

        qs = User.objects.filter(is_active=True)

        if self.q:
            search_fields = [field.replace('user__', '') for field in utils.BASIC_SEARCH_FIELDS]
            qs = utils.get_search_queryset(qs, search_fields, self.q)

        return qs

    def get_result_label(self, item):
        return accounts.utils.get_user_representation(item)

@require_safe
@login_required
def show_indicator_index(request):
    # PERMISSION CHECK
    if not request.user.is_superuser:
        raise PermissionDenied

    teams = Team.objects.all()
    colleges = College.objects.filter(profile__isnull=False)\
                              .distinct()
    exams = Exam.objects.select_related('category')\
                                    .filter(session__isnull=False)\
                                    .distinct()
    sources = Source.objects.all()
    exam_date_json = utils.get_exam_date_json()

    # Feature statistics
    users_active = User.objects.filter(session__isnull=False).distinct().count()
    users_sharing_sessions = (User.objects.filter(session__parent_session__isnull=False) | \
                              User.objects.filter(session__children__isnull=False)).distinct().count()
    users_customizing_theme = User.objects.filter(profile__session_theme__isnull=False).distinct().count()
    users_voting = (User.objects.filter(supported_corrections__isnull=False) | \
                    User.objects.filter(opposed_corrections__isnull=False)).distinct().count()

    context = {'is_indicators_active': True,
               'sources': sources,
               'teams': teams,
               'exams': exams,
               'exam_date_json': exam_date_json,
               'colleges': colleges,
               'users_active': users_active,
               'users_sharing_sessions': users_sharing_sessions,
               'users_customizing_theme': users_customizing_theme,
               'users_voting': users_voting}

    return render(request, "indicators/show_indicator_index.html", context)

@require_safe
@login_required
def show_team_indicators(request, pk):
    # PERMISSION CHECK
    if not request.user.is_superuser:
        raise PermissionDenied

    team = get_object_or_404(Team, pk=pk)
    exams = team.exams.all()

    team_question_pool = Question.objects.undeleted()\
                                         .filter(exam__in=exams)

    context = {'is_indicators_active': True,
               'team': team,
               'team_question_pool': team_question_pool}

    return render(request, "indicators/show_team_indicators.html", context)

@require_safe
@login_required
def show_college_indicators(request, pk):
    # PERMISSION CHECK
    if not request.user.is_superuser:
        raise PermissionDenied

    colleges = College.objects.filter(profile__isnull=False)\
                              .distinct()
    college = get_object_or_404(colleges, pk=pk)
    csv_filename = 'indicators/college-{}.csv'.format(college.pk)

    context = {'is_indicators_active': True,
               'csv_filename': csv_filename,
               'college': college}

    return render(request, "indicators/show_college_indicators.html", context)

@require_safe
@login_required
def show_exam_indicators(request, pk):
    # PERMISSION CHECK
    if not request.user.is_superuser:
        raise PermissionDenied
    exams = Exam.objects.filter(session__isnull=False)\
                                    .distinct()
    exam = get_object_or_404(exams, pk=pk)
    exam_date_json = utils.get_exam_date_json(exam)
    csv_filename = 'indicators/exam-{}.csv'.format(exam.pk)

    context = {'is_indicators_active': True,
               'csv_filename': csv_filename,
               'exam_date_json': exam_date_json,
               'exam': exam}

    return render(request, "indicators/show_exam_indicators.html", context)

@login_required
@require_safe
def get_privileged_file(request, path):
    # PERMISSION CHECK
    if not request.user.is_superuser:
        raise PermissionDenied

    return serve(request, path, settings.PRIVILEGED_DIR, show_indexes=False)

@login_required
@require_safe
def show_about(request):
    team = CoreMember.objects.order_by('?')

    question_count = utils.round_to(Question.objects.undeleted().count(), 100)
    answer_count = utils.round_to(Answer.objects.count(), 100)
    session_count = utils.round_to(Session.objects.count(), 10)
    exam_count = utils.round_to(Exam.objects.count(), 5)

    # An editor is someone who has ever submitted a revision without
    # it being considered a guest contribution.
    editor_count = User.objects.filter(revision__is_contribution=False)\
                               .distinct()\
                               .count()
    editor_count = utils.round_to(editor_count, 5)

    context = {'team': team,
               'question_count': question_count,
               'session_count': session_count,
               'exam_count': exam_count,
               'answer_count': answer_count,
               'editor_count': editor_count}

    return render(request, 'about.html', context)

@login_required
@require_POST
@decorators.ajax_only
@csrf.csrf_exempt
def mark_all_notifications_as_deleted(request):
    request.user.notifications.mark_all_as_deleted()
    return {}
