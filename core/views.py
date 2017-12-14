from dal import autocomplete
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST, require_safe
from django.views.static import serve
import math

from . import utils
from .models import CoreMember
from exams import models as exam_models
from teams import models as team_models
from accounts import models as account_models
import accounts.utils
import teams.utils


@require_safe
def show_index(request):
    if request.user.is_authenticated():

        latest_sessions = request.user.session_set.select_related('exam',
                                                                  'exam__category')\
                                                  .undeleted()\
                                                  .with_accessible_questions()\
                                                  .order_by('-pk')[:8]
        context = {'latest_sessions': latest_sessions}
        if teams.utils.is_editor(request.user):
            revision_pool = exam_models.Revision.objects.undeleted()\
                                                         .filter(submitter=request.user)
            added_question_count = revision_pool.filter(is_first=True).count()
            context['added_question_count'] = added_question_count
            edited_question_count = revision_pool.exclude(is_first=True).count()
            context['edited_question_count'] = edited_question_count
        return render(request, 'index.html', context)

    else:
        question_count = exam_models.Question.objects.undeleted().count()
        answer_count = exam_models.Answer.objects\
                                          .filter(choice__isnull=False)\
                                          .count()
        context = {'question_count': question_count,
                   'answer_count': answer_count}
        return render(request, 'index_unauthenticated.html', context)

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

    teams = team_models.Team.objects.all()
    colleges = account_models.College.objects.filter(profile__isnull=False)\
                                             .distinct()
    exams = exam_models.Exam.objects.filter(session__isnull=False)\
                                    .distinct()
    exam_date_json = utils.get_exam_date_json()

    context = {'is_indicators_active': True,
               'teams': teams,
               'exams': exams,
               'exam_date_json': exam_date_json,
               'colleges': colleges}

    return render(request, "indicators/show_indicator_index.html", context)

@require_safe
@login_required
def show_team_indicators(request, pk):
    # PERMISSION CHECK
    if not request.user.is_superuser:
        raise PermissionDenied

    team = get_object_or_404(team_models.Team, pk=pk)
    categories = team.categories.all()

    team_question_pool = exam_models.Question.objects\
                                             .undeleted()\
                                             .under_categories(categories)

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

    colleges = account_models.College.objects.filter(profile__isnull=False)\
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
    exams = exam_models.Exam.objects.filter(session__isnull=False)\
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

    question_count = utils.round_to(exam_models.Question.objects.undeleted().count(), 100)
    answer_count = utils.round_to(exam_models.Answer.objects.count(), 100)
    session_count = utils.round_to(exam_models.Session.objects.count(), 10)
    exam_count = utils.round_to(exam_models.Exam.objects.count(), 5)

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
