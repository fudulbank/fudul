from dal import autocomplete
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render,get_object_or_404

from accounts.models import Institution, College
from core import decorators
from .models import Exam, Subject, Question, Category, Revision,Source
from . import forms
from teams import utils

def list_meta_categories(request):        
    subcategories = Category.objects.filter(parent_category__isnull=True).user_accessible(request.user)
    context = {"subcategories": subcategories}
    return render(request, 'exams/show_category.html', context)

def show_category(request, slugs):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    # PERMISSION CHECK
    if not category.can_user_access(request.user):
        raise PermissionDenied
    subcategories = category.children.user_accessible(request.user)

    # If this category has one child, just go to it!
    if subcategories.count() == 1:
        subcategory = subcategories.first()
        return HttpResponseRedirect(reverse("exams:show_category",
                                            args=(subcategory.get_slugs(),)))

    exams = Exam.objects.filter(category=category)
    
    context = {'category': category,
               'subcategories': subcategories,
               'exams': exams}

    return render(request, "exams/show_category.html", context)

def add_question(request, slugs, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    exam = get_object_or_404(Exam, pk=pk, category=category)
    context={'exam': exam,}
    if request.method == 'GET':
        questionform = forms.QuestionForm()
        revisionform = forms.RevisionForm()
        revisionchoiceformset = forms.RevisionChoiceFormset()

    context['questionform'] = questionform
    context['revisionform'] = revisionform
    context['revisionchoiceformset'] = revisionchoiceformset
    return render(request, "exams/add-question.html", context)


@decorators.ajax_only
def handel_question(request,exam_pk):

    exam = get_object_or_404(Exam, pk=exam_pk)
    context={'exam': exam}

    if request.method == 'POST':
        instance = Revision(submitter=request.user)
        questionform = forms.QuestionForm(request.POST,
                                          request.FILES)
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
            url = reverse ('exams:add-question', args=(exam.category.get_slugs(),exam.pk))
            full_url = request.build_absolute_uri(url)

            return {"message": "success", "show_url": full_url}



            # return HttpResponseRedirect(reverse('exams:add_question',
            #                                     args=pk))
    elif request.method == 'GET':
        questionform = forms.QuestionForm()
        revisionform = forms.RevisionForm()
        revisionchoiceformset = forms.RevisionChoiceFormset()

    context['questionform'] = questionform
    context['revisionform'] = revisionform
    context['revisionchoiceformset'] = revisionchoiceformset

    return render(request, "exams/add-question.html", context)


class SubjectAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        exam_pk = self.forwarded.get('exam_pk')
        qs = Subject.objects.filter(exam__pk=exam_pk)
        if self.q:
            qs = qs.filter(name=self.q)
        return qs

class SourceAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        exam_pk =  self.forwarded.get('exam_pk')
        exam = Exam.objects.get(pk=exam_pk)
        qs = exam.get_sources()
        if self.q:
            qs = qs.filter(name=self.q)
        return qs


def list_questions(request, slugs, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    exam = get_object_or_404(Exam, pk=pk, category=category)
    approved_questions = Question.objects.filter(subjects__exam=exam,is_deleted=False,status='COMPLETE',revision__is_approved=True)
    pending_questions = Question.objects.filter(subjects__exam=exam,is_deleted=False,status__in=['COMPLETE','SPELLING','INCOMPLETE_ANSWERS','INCOMPLETE_QUESTION'])

    context={'exam': exam,
             'approved_questions': approved_questions,
             'pending_questions':pending_questions}
    return render(request, 'exams/list_questions.html', context)

@decorators.ajax_only
def show_question(request, revision_pk):
    revision = get_object_or_404(Revision,pk=revision_pk)
    context = {'revision': revision}
    return render(request, 'exams/partials/show_question.html', context)


def list_revisions(request, slugs, exam_pk, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404
    exam = get_object_or_404(Exam,pk=exam_pk)
    question = get_object_or_404(Question,pk=pk)
    context = {'question': question,
               'exam': exam}
    return render(request, 'exams/list-revisions.html', context)


def submit_revision(request,slugs,exam_pk, pk):

    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    exam = get_object_or_404(Exam,pk=exam_pk)

    question = get_object_or_404(Question, pk=pk)

    revision = question.get_ultimate_latest_revision()

    context ={'question':question,'revision':revision}

    if request.method == 'POST':

        instance = Revision(submitter=request.user,question=question)

        revisionform = forms.RevisionForm(request.POST,
                                          instance=instance)

        revisionchoiceformset = forms.RevisionChoiceFormset(request.POST)
        if revisionform.is_valid() and revisionchoiceformset.is_valid():
            revision = revisionform.save(commit=False)
            revision.question = question
            if utils.is_editor(request.user):
                if question.status == 'COMPLETE':
                    revision.is_approved == True
                if question.status != 'COMPLETE':
                    revision.is_approved == False
            revision.save()
            revisionchoiceformset.instance = revision
            revisionchoiceformset.save()


        return HttpResponseRedirect(reverse("exams:list_revisions", args=(exam.category.get_slugs(),exam.pk,question.pk)))

    elif request.method == 'GET':
        revisionform = forms.RevisionForm()
        revisionchoiceformset = forms.RevisionChoiceFormset()
    context['revisionform'] = revisionform
    context['revisionchoiceformset'] = revisionchoiceformset

    return render(request, 'exams/submit-revision.html', context)



# def add_question(request, slugs, pk):
#     category = Category.objects.get_from_slugs(slugs)
#     if not category:
#         raise Http404
#
#     exam = get_object_or_404(Exam, pk=pk, category=category)
#     context={'exam':exam}
#     if request.method == 'POST':
#         instance = Revision(submitter=request.user)
#         questionform = forms.QuestionForm(request.POST,
#                                           request.FILES)
#         revisionform = forms.RevisionForm(request.POST,
#                                           instance=instance)
#
#         revisionchoiceformset = forms.RevisionChoiceFormset(request.POST)
#         if questionform.is_valid() and revisionform.is_valid() and revisionchoiceformset.is_valid():
#             question = questionform.save()
#             revision = revisionform.save(commit=False)
#             revision.question = question
#             revision.save()
#             revisionchoiceformset.instance = revision
#             revisionchoiceformset.save()
#
#             if request.user.is_superuser:
#                 if question.status == 'C':
#                     revision.is_approved == True
#                 if question.status != 'C':
#                     revision.is_approved == False













# def submit_revision(request,slugs,exam_pk, pk):
#     category = Category.objects.get_from_slugs(slugs)
#     if not category:
#         raise Http404
#
#     exam = get_object_or_404(Exam,pk=exam_pk)
#
#     question = get_object_or_404(Question, pk=pk)
#
#     revision = question.get_ultimate_latest_revision()
#
#     context ={'question':question,'revision':revision}
#
#     if request.method == 'POST':
#         instance = Revision(submitter=request.user,question=question)
#         revisionform = forms.RevisionForm(request.POST,request.FILES,instance=instance)
#         revisionchoiceformset = forms.RevisionChoiceFormset(request.POST,request.FILES)
#         if revisionform.is_valid() and revisionchoiceformset.is_valid():
#             revision = revisionform.save()
#             revisionchoiceformset.instance = revision
#             revisionchoiceformset.save()
#         return HttpResponseRedirect(reverse("exams:list_revisions", args=(exam.category.get_slugs(),exam.pk,question.pk)))
#
#     elif request.method == 'GET':
#         revisionform =forms.RevisionForm(instance=revision)
#         revisionchoiceformset = forms.RevisionChoiceFormset(instance=revision)
#     context['revisionform'] = revisionform
#     context['revisionchoiceformset'] = revisionchoiceformset
#
#     return render(request, 'exams/submit-revision.html', context)





