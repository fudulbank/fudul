from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import strip_tags
from django.views.decorators import csrf
from django.views.decorators.http import require_POST, require_safe
from post_office import mail

from core import decorators
from . import forms
from .models import *


@require_safe
@login_required
def list_messages(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    messages = Message.objects.all()
    return render(request, 'mailer/list_messages.html',
                  {'messages': messages})

@login_required
def create_message(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    if request.method == 'GET':
        form = forms.MessageForm()
    elif request.method == 'POST':
        instance = Message(submitter=request.user)
        form = forms.MessageForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('mailer:list_messages'))

    return render(request, 'mailer/create_message.html',
                  {'form': form})

@require_POST
@login_required
@decorators.ajax_only
@csrf.csrf_exempt
def send_test_message(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    form = forms.MessageTestForm(request.POST)
    if form.is_valid():
        if not request.user.email:
            raise Exception("No registered email address for you.")

        if hasattr(request.user, 'profile') and \
           request.user.profile.alternative_email:
            cc_address = request.user.profile.alternative_email
        else:
            cc_address = None

        from_address = form.cleaned_data['from_address']
        subject = form.cleaned_data['subject']
        body = form.cleaned_data['body']
        try:
            mail.send(request.user.email, from_address, cc=cc_address,
                      subject=subject, message=strip_tags(body),
                      html_message=body)
        except ValidationError:
            raise Exception("Invalid email address is registered.")
    else:
        raise Exception("We do not have valid message fields.")

    return {}
