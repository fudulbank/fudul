from dal import autocomplete
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_safe
import math

from . import utils
from .models import CoreMember
from exams import models as exams_models
import accounts.utils
import teams.utils


@require_safe
def show_index(request):
    if request.user.is_authenticated():

        latest_sessions = exams_models.Session.objects.filter(submitter=request.user)\
                                                      .with_accessible_questions()\
                                                      .order_by('-pk')[:8]
        context = {'latest_sessions': latest_sessions}
        if teams.utils.is_editor(request.user):
            revision_pool = exams_models.Revision.objects.undeleted()\
                                                         .filter(submitter=request.user)
            added_question_count = revision_pool.filter(is_first=True).count()
            context['added_question_count'] = added_question_count
            edited_question_count = revision_pool.exclude(is_first=True).count()
            context['edited_question_count'] = edited_question_count
        return render(request, 'index.html', context)

    else:
        question_count = exams_models.Question.objects.undeleted().count()
        answer_count = exams_models.Answer.objects\
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

@login_required
@require_safe
def show_about(request):
    team = CoreMember.objects.order_by('?')

    question_count = utils.round_to(exams_models.Question.objects.undeleted().count(), 100)
    answer_count = utils.round_to(exams_models.Answer.objects.count(), 100)
    session_count = utils.round_to(exams_models.Session.objects.count(), 10)
    exam_count = utils.round_to(exams_models.Exam.objects.count(), 5)
    editor_count = utils.round_to(User.objects.filter(team_memberships__isnull=False).count(), 5)

    context = {'team': team,
               'question_count': question_count,
               'session_count': session_count,
               'exam_count': exam_count,
               'answer_count': answer_count,
               'editor_count': editor_count}

    return render(request, 'about.html', context)
