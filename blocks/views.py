from django.shortcuts import render,get_object_or_404
from django.core.urlresolvers import reverse
from accounts.models import Institution,College
from blocks.models import Year,Block,Subject,Question
from core import decorators
from blocks import forms
# Create your views here.


def list_institutions(request):
    institutions = Institution.objects.all()
    context = {'institutions':institutions}
    return render(request,'blocks/list_institutions.html',context)


def list_colleges(request,pk):
    institution = get_object_or_404(Institution, pk=pk)
    colleges = College.objects.filter(institution=institution)
    context ={'colleges':colleges}
    return render(request,'blocks/list_colleges.html',context)


def list_years(request,pk):
    college = get_object_or_404(College,pk=pk)
    years = Year.objects.filter(college=college)
    context = {'year': years}
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
def handle_block(request,year_pk):
    year = get_object_or_404(Year,pk=year_pk)

    context = {'year':year}

    if request.method == 'POST':
        form = forms.BlockForm(request.POST,year=year)
        if form.is_valid():
            form.save(submitter=request.user)
            show_url= reverse('blocks:list_blocks')
            return {"message": "success", "show_url": show_url}
    elif request.method == 'GET':
        form = forms.BlockForm(year=year)
    context['form'] = form
    return render(request, 'blocks/partials/add_block.html', context)

@decorators.ajax_only
def handle_question(request, subject_pk):
    subject = get_object_or_404(Subject, pk=subject_pk)

    context = {'subject':subject}

    if request.method == 'POST':
        instance = Question(subject=subject, submitter=request.user)
        form = forms.QuestionForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            show_url = reverse('blocks:list_subjects')
            full_url = request.build_absolute_uri(show_url)
            return {"message": "success", "show_url": show_url}
    elif request.method == 'GET':
        instance = Question(subject=subject, submitter=request.user)
        form = forms.QuestionForm(instance=instance)
    context['form'] = form

    return render(request,'blocks/partials/submit_question.html')

