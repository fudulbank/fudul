from django.shortcuts import render,get_object_or_404
from django.core.urlresolvers import reverse
from accounts.models import Institution,College
from blocks.models import Year,Block,Subject,Question
from core import decorators
from blocks import forms
from django.http import HttpResponse, HttpResponseRedirect, Http404

from django.contrib.auth.models import User
# Create your views here.


def list_institutions(request):
    institutions = Institution.objects.all()
    context = {'institutions': institutions}
    return render(request, 'index.html', context)


def list_colleges(request,pk):
    institution = get_object_or_404(Institution, pk=pk)
    colleges = College.objects.filter(institution=institution)
    context ={'colleges':colleges}
    return render(request,'blocks/list_colleges.html',context)


def list_years(request,pk):
    college = get_object_or_404(College,pk=pk)
    years = Year.objects.filter(college=college)
    context = {'years': years}
    return render(request,'blocks/list_years.html',context)


def list_blocks(request,pk):
    year = get_object_or_404(Year, pk=pk)
    blocks = Block.objects.filter(year=year)
    context = {'blocks': blocks}
    return render(request,'blocks/list_blocks.html',context)


def list_subjects(request,pk):
    block = get_object_or_404(Block, pk=pk)
    subjects = Subject.objects.filter(block=block)
    context ={'subjects':subjects}
    return render(request,'blocks/list_subjects.html',context)


@decorators.ajax_only
def handle_block(request, year_pk):
    year = get_object_or_404(Year,pk=year_pk)

    context = {'year': year}

    if request.method == 'POST':
        instance =Block(year=year,submitter=request.user)
        form = forms.BlockForm(request.POST,instance=instance)
        if form.is_valid():
            form.save()
            show_url= reverse('blocks:list_blocks')
            return {"message": "success", "show_url": show_url}
    elif request.method == 'GET':
        form = forms.BlockForm()
    context['form'] = form
    return render(request, 'blocks/partials/add_block.html', context)

@decorators.ajax_only

def handle_question(request, subject_pk):
    subject = get_object_or_404(Subject, pk=subject_pk)
    context = {'subject': subject}

    if request.method == 'POST':
        instance = Question(subject=subject,submitter=request.user)
        form = forms.QuestionForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            show_url = reverse('blocks:list_subjects')
            full_url = request.build_absolute_uri(show_url)
            context['form'] = form
            return {"message": "success", "show_url": show_url}
    elif request.method == 'GET':
        form = forms.QuestionForm()
    context['form'] = form


    return render(request,'blocks/partials/submit_question.html',context)

def list_questions(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    questions = Question.objects.filter(subject=subject)
    context = {'questions':questions}
    return render(request,'blocks/list_questions.html',context)

def add_question(request):
    context={}
    if request.method == 'POST':
        form= forms.QuestionForm(request.POST,request.FILES,submitter=request.user)
        if form.is_valid() :
            question = form.save()
            return HttpResponseRedirect(reverse('blocks:add_question'))
    elif request.method == 'GET':
        form= forms.QuestionForm()
    context['form'] = form
    return render(request, 'blocks/add_question_form.html', context)




