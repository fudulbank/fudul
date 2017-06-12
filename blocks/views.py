from django.shortcuts import render,get_object_or_404
from django.core.urlresolvers import reverse
from accounts.models import Institution,College
from accounts.utils import get_user_institution
from blocks.models import Year,Exam,Subject,Question,Category,Revision,Source
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


def list_exams(request,pk):
    year = get_object_or_404(Year, pk=pk)
    blocks = Exam.objects.filter(year=year)
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
        form = forms.ExamForm(request.POST,instance=instance)
        if form.is_valid():
            form.save()
            show_url= reverse('blocks:list_exams')
            return {"message": "success", "show_url": show_url}
    elif request.method == 'GET':
        form = forms.ExamForm()
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

# def add_question(request):
#     context={}
#     if request.method == 'POST':
#         form= forms.QuestionForm(request.POST,request.FILES,submitter=request.user)
#         if form.is_valid() :
#             question = form.save()
#             return HttpResponseRedirect(reverse('blocks:add_question'))
#     elif request.method == 'GET':
#         form= forms.QuestionForm()
#     context['form'] = form
#     return render(request, 'blocks/add_question_form.html', context)


def list_meta_categories(request):
    categories=Category.objects.filter(parent_category__isnull=True)
    context = {"categories":categories}
    return render(request,'blocks/list-categories.html',context)


def list_categories(request,slug):

    category = get_object_or_404(Category, slug=slug)
    categories = Category.objects.filter(parent_category=category)
    last_categories = Category.objects.filter(children__isnull=True)
    context = {'categories': categories,'last_categories':last_categories}
    for a in last_categories:
        if Exam.objects.filter(parent_category=a, is_deleted=False).exists():
            exams = Exam.objects.filter(parent_category=a,is_deleted=False)
            context['exams'] = exams

    return render(request, "blocks/list-categories.html", context)



def add_question(request,pk):
    exam = get_object_or_404(Exam,pk=pk)
    sources = Source.objects.all()
    context={'exam':exam,'sources':sources}
    if request.method == 'POST':
        instance = Revision(submitter=request.user)
        questionform = forms.QuestionForm(request.POST,
                                          request.FILES,
                                          user=request.user,
                                          exam=exam)
        revisionform = forms.RevisionForm(request.POST,
                                          instance=instance)

        revisionchoiceformset = forms.RevisionChoiceFormset(request.POST)
        if questionform.is_valid() and revisionform.is_valid() and revisionchoiceformset.is_valid():
            question = questionform.save()
            revision = revisionform.save(commit=False)
            revision.question = question
            submit_revision = revision.save()
            revisionchoiceformset.instance = submit_revision
            revisionchoiceformset.save()
            return HttpResponseRedirect(reverse('blocks:add_question',
                                                args=exam.pk))
    elif request.method == 'GET':
        questionform = forms.QuestionForm(user=request.user)
        revisionform = forms.RevisionForm()
        revisionchoiceformset = forms.RevisionChoiceFormset()

    context['questionform'] = questionform
    context['revisionform'] = revisionform
    context['revisionchoiceformset'] = revisionchoiceformset

    return render(request, "blocks/add-question.html", context)






