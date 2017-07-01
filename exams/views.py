from dal import autocomplete
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template
from django.views.decorators import csrf

from core import decorators
from .models import Exam, Question, Category, Revision,Session,Choice
from . import forms, utils
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
               'subcategories': subcategories.order_by('name'),
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
               'questionform': forms.QuestionForm(exam=exam),
               'revisionform': forms.RevisionForm(),
               'revisionchoiceformset': forms.RevisionChoiceFormset()}

    return render(request, "exams/add_question.html", context)

class QuestionAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        exam_pk = self.forwarded.get('exam_pk')
        exam = Exam.objects.get(pk=exam_pk)
        qs = exam.get_questions().order_by_submission()
        if self.q:
            qs = qs.filter(pk=self.q)
        return qs

    def get_result_label(self, item):
        text_preview = str(item)
        return "<strong>{}</strong>: {}".format(item.pk, text_preview)

@csrf.csrf_exempt
@decorators.post_only
@decorators.ajax_only
def delete_question(request, pk):
    question = get_object_or_404(Question, pk=pk)
    exam = question.get_exam()

    # PERMISSION CHECK
    if not request.user.is_superuser and \
       not exam.category.is_user_editor(request.user) and \
       not question.is_user_creator(user):
        raise Exception("You cannot delete that question!")

    question.is_deleted = True
    question.save()

    return {}

@decorators.post_only
@decorators.ajax_only
def handle_question(request, exam_pk):
    exam = get_object_or_404(Exam, pk=exam_pk)

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    instance = Revision(submitter=request.user, is_first=True,
                        is_last=True)
    questionform = forms.QuestionForm(request.POST,
                                      request.FILES,
                                      exam=exam)
    revisionform = forms.RevisionForm(request.POST,
                                      instance=instance)
    revisionchoiceformset = forms.RevisionChoiceFormset(request.POST)

    if questionform.is_valid() and revisionform.is_valid() and revisionchoiceformset.is_valid():
        question = questionform.save()
        revision = revisionform.save(commit=False)
        revision.question = question
        revision.save()
        revisionform.save_m2m()

        if teams.utils.is_editor(request.user) and \
           revision.statuses.filter(code_name='COMPLETE').exists():
            revision.is_approved = True
        else:
            revision.is_approved = False
        revision.save()

        revisionchoiceformset.instance = revision
        revisionchoiceformset.save()

        template = get_template('exams/partials/exam_stats.html')
        context = {'exam': exam}
        stat_html = template.render(context)

        return {"message": "success",
                "question_pk": question.pk,
                "stat_html": stat_html}

    context = {'exam': exam,
               'questionform': questionform,
               'revisionform': revisionform,
               'revisionchoiceformset': revisionchoiceformset}

    return render(request, "exams/partials/question_form.html", context)

@login_required
def list_questions(request, slugs, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    exam = get_object_or_404(Exam, pk=pk, category=category)

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context={'exam': exam}
    return render(request, 'exams/list_questions.html', context)

@login_required
@decorators.ajax_only
def show_question(request, pk, revision_pk=None):
    question = get_object_or_404(Question, pk=pk)
    if revision_pk:
        revision = get_object_or_404(Revision, pk=revision_pk)
    else:
        revision = question.get_latest_revision()

    exam = question.get_exam()

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
    latest_revision = question.get_latest_revision()

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context ={'exam':exam, 'revision': latest_revision}

    if request.method == 'POST':
        questionform = forms.QuestionForm(request.POST,
                                          request.FILES,
                                          instance=question,
                                          exam=exam)
        revisionform = forms.RevisionForm(request.POST,
                                          instance=latest_revision)

        revisionchoiceformset = forms.RevisionChoiceFormset(request.POST,
                                                            instance=latest_revision)
        if questionform.is_valid() and revisionform.is_valid() and revisionchoiceformset.is_valid():
            question = questionform.save()
            new_revision = revisionform.save(commit=False)
            # Setting primary key to None creates a new object, rather
            # than modifying the pre-existing one
            new_revision.pk = None
            new_revision.submitter = request.user
            new_revision.save()
            revisionform.save_m2m()

            # Make sure that all previous revisions are set to
            # is_last=False
            question.revision_set.exclude(pk=new_revision.pk)\
                                 .update(is_last=False)

            if teams.utils.is_editor(request.user) and \
               new_revision.statuses.filter(code_name='COMPLETE').exists():
                new_revision.is_approved = True
            else:
                new_revision.is_approved = False

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
        questionform = forms.QuestionForm(instance=question, exam=exam)
        revisionform = forms.RevisionForm(instance=latest_revision)
        revisionchoiceformset = forms.RevisionChoiceFormset(instance=latest_revision)
    context['questionform'] = questionform
    context['revisionform'] = revisionform
    context['revisionchoiceformset'] = revisionchoiceformset

    return render(request, 'exams/submit_revision.html', context)

@login_required
def list_question_per_status(request, slugs, exam_pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    exam = get_object_or_404(Exam, pk=exam_pk)
    question_pool = Question.objects.undeleted().filter(subjects__exam=exam).distinct()
    writing_error = question_pool.filter(statuses__code_name='WRITING_ERROR')
    unsloved = question_pool.filter(statuses__code_name='UNSOLVED')
    incomplete_answer = question_pool.filter(statuses__code_name='INCOMPLETE_ANSWERS')
    incomplete_question = question_pool.filter(statuses__code_name='INCOMPLETE_QUESTION')
    context ={'writing_error':writing_error, 'unsloved':unsloved, 'incomplete_answer':incomplete_answer,
              'incomplete_question':incomplete_question,'exam':exam}
    return render(request, 'exams/list_question_per_status.html', context)
#
# @login_required
# def start_session(request, slugs, exam_pk):
#     category = Category.objects.get_from_slugs(slugs)
#     if not category:
#         raise Http404
#
#     # PERMISSION CHECK
#     exam = get_object_or_404(Exam, pk=exam_pk, category=category)
#     if not exam.can_user_edit(request.user):
#         raise PermissionDenied
#
#     context = {'exam': exam}
#     if request.method == 'POST':
#         instance = Session(submitter=request.user, exam=exam)
#         sessionform = forms.SessionForm(request.POST,
#                                         request.FILES,
#                                         instance=instance)
#         if sessionform.is_valid():
#             sessionform.save()
#         # return HttpResponseRedirect(reverse("exams:list_revisions", args=(exam.category.get_slugs(), exam.pk, question.pk)))
#     elif request.method == 'GET':
#         sessionform = forms.SessionForm()
#
#     context['sessionform'] = sessionform
#
#     return render(request, "exams/start_session.html", context)


@decorators.get_only
@login_required
def start_session(request, slugs, exam_pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    # PERMISSION CHECK
    exam = get_object_or_404(Exam, pk=exam_pk, category=category)
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    question_count = exam.get_approved_questions().count()

    context = {'exam': exam,
               'sessionform': forms.SessionForm(),
               'question_count':question_count}

    return render(request, "exams/start_session.html", context)


@decorators.post_only
@decorators.ajax_only
def handle_session(request,exam_pk):
    exam = get_object_or_404(Exam, pk=exam_pk)

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    instance = Session(submitter=request.user, exam=exam)
    sessionform = forms.SessionForm(request.POST,
                                      request.FILES,
                                    instance=instance)

    if sessionform.is_valid():
        session = sessionform.save()
        show_url = reverse('exams:session', args=(session.exam.category.get_slugs(),session.exam.pk,session.pk))
        full_url = request.build_absolute_uri(show_url)
        return {"message": "success",
                "show_url":full_url}

    context = {'exam': exam,
               'sessionform': sessionform,}

    return render(request, "exams/start_session.html", context)

@decorators.post_only
@decorators.ajax_only
@csrf.csrf_exempt

def start_session_ajax(request,session_pk):
    session = get_object_or_404(Session,pk=session_pk)
    exam = session.exam
    subjects = []
    sources = []

    for subject in session.subjects.all():
        subjects.append(subject)

    for source in session.sources.all():
        sources.append(source)

    # question_pool = Question.objects.filter(exam_type=session.session_type,statuses__code_name='COMPLETE',subjects__in=subjects, sources__in=sources)

    output = {"questions": [],
              'session_pk':session.pk }

    for question in exam.get_approved_questions():
        choices = []
        content = []
        if question.get_latest_approved_revision():
            revision = question.get_latest_approved_revision()
            content.append({"text": revision.text,'pk':question.pk})
            for choice in revision.choice_set.all():
                choices.append({"pk": choice.pk, "text": choice.text,'is_answer': choice.is_answer})
            if revision.explanation :
                content.append({"explanation": revision.explanation})
            if revision.figure:
                content.append({"figure": revision.figure.url})
        question_result = {'content': content,
                           'choices': choices,
                           }
        output["questions"].append(question_result)

    return output

def session(request, slugs, exam_pk,session_pk):
    category = Category.objects.get_from_slugs(slugs)
    session = get_object_or_404(Session,pk=session_pk)

    if not category:
        raise Http404

    # PERMISSION CHECK
    exam = get_object_or_404(Exam, pk=exam_pk, category=category)
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    return render(request, "exams/solved_session.html",{'session':session})


@decorators.ajax_only
@decorators.post_only
@login_required
@csrf.csrf_exempt
def check_answer(request):
    choice_pk = request.POST.get('choice_pk')
    choice = get_object_or_404(Choice, pk=choice_pk)
    question_pk = request.POST.get('question_pk')
    question = get_object_or_404(Question,pk=question_pk)
    session_pk = request.POST.get('session_pk')
    session = get_object_or_404(Session, pk=session_pk)

    if choice.is_answer:
        right= True
    else:
        right = False
    score = session.right_answers
    return {"right":right,"score":score}
