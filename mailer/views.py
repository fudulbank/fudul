from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse

from . import forms
from .models import *


def list_messages(request):
    messages = Message.objects.all()
    return render(request, 'mailer/list_messages.html',
                  {'messages': messages})

def create_message(request):
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
