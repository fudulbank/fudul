from django.shortcuts import render,get_object_or_404
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from accounts.models import Institution,College
from blocks.models import Year,Exam,Subject,Question,Category,Revision
from core import decorators
from blocks import forms
from teams import utils
from django.http import HttpResponse, HttpResponseRedirect, Http404

from django.contrib.auth.models import User


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
    subcategories = Category.objects.filter(parent_category__isnull=True).user_accessible(request.user)
    context = {"subcategories": subcategories}
    return render(request, 'blocks/show_category.html', context)

def show_category(request, slugs):
    slug_list = [slug for slug in slugs.split('/') if slug]
    last_slug = slug_list.pop(-1)
    kwargs = {'slug': last_slug}
    level = 'parent_category'
    for slug in slug_list:
        kwarg = level + '__slug'
        kwargs[kwarg] = slug
        level += '__parent_category'
    category = get_object_or_404(Category, **kwargs)

    # PERMISSION CHECK
    if not category.can_user_access(request.user):
        raise PermissionDenied
    subcategories = category.children.user_accessible(request.user)

    # If this category has one child, just go to it!
    if subcategories.count() == 1:
        subcategory = subcategories.first()
        return HttpResponseRedirect(reverse("blocks:show_category",
                                            args=(subcategory.get_slugs(),)))

    exams = Exam.objects.filter(category=category)
    
    context = {'category': category,
               'subcategories': subcategories,
               'exams': exams}

    return render(request, "blocks/show_category.html", context)

def add_question(request,pk):
    exam = get_object_or_404(Exam,pk=pk)
    context={'exam':exam}
    if request.method == 'POST':
        instance = Revision(submitter=request.user)
        questionform = forms.QuestionForm(request.POST,
                                          request.FILES,
                                          user=request.user,
                                          )
        revisionform = forms.RevisionForm(request.POST,
                                          instance=instance)

        revisionchoiceformset = forms.RevisionChoiceFormset(request.POST)
        if questionform.is_valid() and revisionform.is_valid() and revisionchoiceformset.is_valid():
            question = questionform.save()
            revision = revisionform.save(commit=False)
            revision.question = question
            revision.save()
            revisionchoiceformset.instance = revision
            revisionchoiceformset.save()

            if request.user.is_superuser:
                if question.status == 'C':
                    revision.is_approved == True
                if question.status != 'C':
                    revision.is_approved == False


            # return HttpResponseRedirect(reverse('blocks:add_question',
            #                                     args=pk))
    elif request.method == 'GET':
        questionform = forms.QuestionForm(user=request.user)
        revisionform = forms.RevisionForm()
        revisionchoiceformset = forms.RevisionChoiceFormset()

    context['questionform'] = questionform
    context['revisionform'] = revisionform
    context['revisionchoiceformset'] = revisionchoiceformset

    return render(request, "blocks/add-question.html", context)


def list_questions(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    approved_questions = Question.objects.filter(subject__exam=exam,is_deleted=False,status='C')
    pending_questions = Question.objects.filter(subject__exam=exam,is_deleted=False,status__in=['S','A','Q'])
    context={'approved_questions':approved_questions,'pending_questions':pending_questions}
    return render(request,'blocks/list_questions.html',context)

@decorators.ajax_only
def show_question(request,revision_pk):
    revision= get_object_or_404(Revision,pk=revision_pk)
    context = {'revision':revision}
    return render(request,'blocks/partials/show_question.html',context)






