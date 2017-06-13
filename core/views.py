from django.shortcuts import render
from accounts.models import Institution
from blocks.models import Category
from accounts import utils
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required



def show_index(request):
    if request.user.is_authenticated():
        return render(request, 'index.html')
    else:
        return render(request, 'index_unauthenticated.html')
