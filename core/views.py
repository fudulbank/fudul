from dal import autocomplete
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render

from . import utils
from exams.models import Answer, Question 
import accounts.utils


def show_index(request):
    if request.user.is_authenticated():
        return render(request, 'index.html')
    else:
        question_count = Question.objects.undeleted().count()
        answer_count = Answer.objects.count()
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
