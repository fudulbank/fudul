from dal import autocomplete
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render,get_object_or_404

from accounts.models import Institution, College
from core import decorators
from .models import Exam, Subject, Question, Category, Revision,Source
from . import forms
import teams.utils


@login_required
def list_meta_categories(request):
    subcategories = Category.objects.filter(parent_category__isnull=True).user_accessible(request.user)
    context = {"subcategories": subcategories}
    return render(request, 'exams/show_category.html', context)

@login_required
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

@decorators.get_only
@login_required
def add_question(request, slugs, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    # PERMISSION CHECK
    exam = get_object_or_404(Exam, pk=pk, category=category)
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context = {'exam': exam,
               'questionform': forms.QuestionForm(),
               'revisionform': forms.RevisionForm(),
               'revisionchoiceformset': forms.RevisionChoiceFormset()}

    return render(request, "exams/add_question.html", context)

@decorators.post_only
@decorators.ajax_only
def handle_question(request, exam_pk):
    exam = get_object_or_404(Exam, pk=exam_pk)

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    instance = Revision(submitter=request.user)
    questionform = forms.QuestionForm(request.POST,
                                      request.FILES)
    revisionform = forms.RevisionForm(request.POST,
                                      instance=instance)
    revisionchoiceformset = forms.RevisionChoiceFormset(request.POST)

    if questionform.is_valid() and revisionform.is_valid() and revisionchoiceformset.is_valid():
        question = questionform.save()
        revision = revisionform.save(commit=False)
        if teams.utils.is_editor(request.user):
            revision.is_approved = True
        revision.question = question
        revision.save()
        revisionchoiceformset.instance = revision
        revisionchoiceformset.save()
        return {"message": "success"}

    context = {'exam': exam,
               'questionform': questionform,
               'revisionform': revisionform,
               'revisionchoiceformset': revisionchoiceformset}

    return render(request, "exams/partials/question_form.html", context)

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

@login_required
def list_questions(request, slugs, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    exam = get_object_or_404(Exam, pk=pk, category=category)

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied
    approved_questions =[]
    pending_questions =[]
    question_pool = Question.objects.filter(subjects__exam=exam, is_deleted=False).distinct()
    complete_questions = question_pool.filter(status='COMPLETE')
    incomplete_questions = question_pool.filter(status__in=['SPELLING', 'INCOMPLETE_ANSWERS',
                                                            'INCOMPLETE_QUESTION'])
    for question in complete_questions:
        if question.revision_set.filter(is_approved=True).count()>=1:
            approved_questions.append(question)
        else:
            pending_questions.append(question)

    for question in incomplete_questions:
        pending_questions.append(question)

    context={'exam': exam,
             'approved_questions': approved_questions,
             'pending_questions':pending_questions}
    return render(request, 'exams/list_questions.html', context)

@login_required
@decorators.ajax_only
def show_question(request, revision_pk):
    revision = get_object_or_404(Revision,pk=revision_pk)
    exam = revision.question.get_exam()

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context = {'revision': revision}
    return render(request, 'exams/partials/show_question.html', context)

@login_required
def list_revisions(request, slugs, exam_pk, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404
    exam = get_object_or_404(Exam, pk=exam_pk)

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    question = get_object_or_404(Question,pk=pk)
    context = {'question': question,
               'exam': exam}
    return render(request, 'exams/list_revisions.html', context)

@login_required
def submit_revision(request,slugs,exam_pk, pk):

    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    exam = get_object_or_404(Exam, pk=exam_pk)
    question = get_object_or_404(Question, pk=pk)
    latest_revision = question.get_ultimate_latest_revision()

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context ={'exam':exam, 'revision': latest_revision}

    if request.method == 'POST':
        revisionform = forms.RevisionForm(request.POST,
                                          instance=latest_revision)

        revisionchoiceformset = forms.RevisionChoiceFormset(request.POST,
                                                            instance=latest_revision)
        if revisionform.is_valid() and revisionchoiceformset.is_valid():
            new_revision = revisionform.save(commit=False)
            new_revision.question = question
            if teams.utils.is_editor(request.user):
                new_revision.is_approved = True
            # Setting primary key to None creates a new object, rather
            # than modifying the pre-existing one
            new_revision.pk = None
            new_revision.submitter = request.user
            new_revision.save()

            # Let's clone choices!
            modified_choices = revisionchoiceformset.save(commit=False)
            unmodified_choices = []
            for choice in revisionchoiceformset.queryset:
                if not choice in revisionchoiceformset.deleted_objects and \
                   not choice in modified_choices:
                    unmodified_choices.append(choice)
            choices = modified_choices + unmodified_choices
            for choice in choices:
                choice.pk = None
                choice.revision = new_revision
                choice.save()

            return HttpResponseRedirect(reverse("exams:list_revisions", args=(exam.category.get_slugs(),exam.pk,question.pk)))

    elif request.method == 'GET':
        revisionform = forms.RevisionForm(instance=latest_revision)
        revisionchoiceformset = forms.RevisionChoiceFormset(instance=latest_revision)

    context['revisionform'] = revisionform
    context['revisionchoiceformset'] = revisionchoiceformset

    return render(request, 'exams/submit_revision.html', context)
