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
from .models import Exam, Question, Category, Revision, Session, Choice, Answer
from . import forms, utils
import teams.utils


@login_required
def list_meta_categories(request, indicators=False):
    if indicators and not teams.utils.is_editor(request.user):
        raise PermissionDenied

    if indicators:
        show_category_url = 'exams:show_category_indicators'
    else:
        show_category_url = 'exams:show_category'

    subcategories = Category.objects.filter(parent_category__isnull=True).user_accessible(request.user)
    context = {"subcategories": subcategories,
               'show_category_url': show_category_url,
               'indicators': indicators}
    return render(request, 'exams/show_category.html', context)


@login_required
def show_category(request, slugs, indicators=False):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    if indicators:
        show_category_url = 'exams:show_category_indicators'
        exams = None
    else:
        show_category_url = 'exams:show_category'
        exams = Exam.objects.filter(category=category)
    
    # PERMISSION CHECK
    if not category.can_user_access(request.user):
        raise PermissionDenied
    subcategories = category.children.user_accessible(request.user)
    
    # If this category has one child, just go to it!
    if subcategories.count() == 1:
        subcategory = subcategories.first()
        return HttpResponseRedirect(reverse(show_category_url,
                                            args=(subcategory.get_slugs(),)))
    elif subcategories.count() == 0 and indicators:
        return show_category_indicators(request, category)

    context = {'category': category,
               'show_category_url': show_category_url,
               'exams': exams,
               'subcategories': subcategories.order_by('name'),
               'indicators': indicators}

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
            not question.is_user_creator(request.user):
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
                                      exam=exam)
    revisionform = forms.RevisionForm(request.POST,
                                      request.FILES,
                                      instance=instance)
    revisionchoiceformset = forms.RevisionChoiceFormset(request.POST)

    if questionform.is_valid() and revisionform.is_valid() and revisionchoiceformset.is_valid():
        question = questionform.save()
        revision = revisionform.save(commit=False)
        revision.question = question
        revision.save()
        revisionform.save_m2m()

        if utils.test_revision_approval(revision, request.user):
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

    context = {'exam': exam}
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

    question = get_object_or_404(Question, pk=pk)
    context = {'question': question,
               'exam': exam}
    return render(request, 'exams/list_revisions.html', context)


@login_required
def submit_revision(request, slugs, exam_pk, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    exam = get_object_or_404(Exam, pk=exam_pk)
    question = get_object_or_404(Question, pk=pk)
    latest_revision = question.get_latest_revision()

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context = {'exam': exam, 'revision': latest_revision}

    if request.method == 'POST':
        questionform = forms.QuestionForm(request.POST,
                                          instance=question,
                                          exam=exam)
        revisionform = forms.RevisionForm(request.POST,
                                          request.FILES,
                                          instance=latest_revision)

        revisionchoiceformset = forms.RevisionChoiceFormset(request.POST,
                                                            instance=latest_revision)
        if questionform.is_valid() and revisionform.is_valid() and revisionchoiceformset.is_valid():
            question = questionform.save()
            new_revision = revisionform.clone(question, request.user)
            revisionchoiceformset.clone(new_revision)
            return HttpResponseRedirect(
                reverse("exams:list_revisions", args=(exam.category.get_slugs(), exam.pk, question.pk)))

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
    context = {'writing_error': writing_error, 'unsloved': unsloved, 'incomplete_answer': incomplete_answer,
               'incomplete_question': incomplete_question, 'exam': exam}
    return render(request, 'exams/list_question_per_status.html', context)

@decorators.get_only
@login_required
def create_session(request, slugs, exam_pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    # PERMISSION CHECK
    exam = get_object_or_404(Exam, pk=exam_pk, category=category)
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    question_count = exam.get_approved_questions().count()

    context = {'exam': exam,
               'sessionform': forms.SessionForm(exam=exam),
               'question_count': question_count}

    return render(request, "exams/create_session.html", context)


@decorators.post_only
@decorators.ajax_only
def handle_session(request, exam_pk):
    exam = get_object_or_404(Exam, pk=exam_pk)

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    instance = Session(submitter=request.user, exam=exam)
    sessionform = forms.SessionForm(request.POST, request.FILES,
                                    instance=instance, exam=exam)

    if sessionform.is_valid():
        session = sessionform.save()
        show_url = reverse('exams:show_session', args=(session.exam.category.get_slugs(), session.exam.pk, session.pk))
        full_url = request.build_absolute_uri(show_url)
        return {"message": "success",
                "show_url": full_url}

    context = {'exam': exam,
               'sessionform': sessionform, }

    return render(request, "exams/create_session.html", context)


@login_required
def show_session(request, slugs, exam_pk, session_pk, question_pk=None):
    category = Category.objects.get_from_slugs(slugs)
    session = get_object_or_404(Session, pk=session_pk)

    if not category:
        raise Http404

    # PERMISSION CHECK
    if not session.submitter == request.user and \
       not request.user.is_superuser:
        raise PermissionDenied

    if question_pk:
        if not session.questions.filter(pk=question_pk).exists():
            raise Http404
        question = session.questions.get(pk=question_pk)
    else:
        unused_questions = session.get_unused_questions()
        question = unused_questions.first()

    question_sequence = session.get_question_sequence(question)

    return render(request, "exams/show_session.html", {'session': session,
                                                       'question': question,
                                                       'question_sequence': question_sequence})

@decorators.ajax_only
@decorators.post_only
@login_required
@csrf.csrf_exempt
def toggle_marked(request):
    question_pk = request.POST.get('question_pk')
    session_pk = request.POST.get('session_pk')
    
    question = get_object_or_404(Question, pk=question_pk)
    session = get_object_or_404(Session, pk=session_pk)

    if utils.is_question_marked(question, session):
        session.is_marked.remove(question)
        is_marked = False
    else:
        session.is_marked.add(question)
        is_marked = True

    return {'is_marked': is_marked}

@decorators.ajax_only
@decorators.post_only
@login_required
@csrf.csrf_exempt
def get_previous_question(request):
    question_pk = request.POST.get('question_pk')
    session_pk = request.POST.get('session_pk')
    question = get_object_or_404(Question, pk=question_pk)
    session = get_object_or_404(Session, pk=session_pk)

    previous_question = session.questions.order_by('pk').exclude(pk__gte=question.pk).last()
    question_sequence = session.get_question_sequence(previous_question)
    template = get_template('exams/partials/session-question.html')
    context = {'question': previous_question, 'session': session}
    question_body = template.render(context)
    is_marked = utils.is_question_marked(previous_question, session)
    url = previous_question.get_session_url(session)

    return {"is_marked": is_marked,
            'url': url,
            'question_sequence': question_sequence,
            'question_pk': previous_question.pk,
            "question_body": question_body}
    
@decorators.ajax_only
@decorators.post_only
@login_required
@csrf.csrf_exempt
def check_answer(request):
    question_pk = request.POST.get('question_pk')
    session_pk = request.POST.get('session_pk')
    choice_pk = request.POST.get('choice_pk') or None

    question = get_object_or_404(Question, pk=question_pk)
    session = get_object_or_404(Session, pk=session_pk)
    if choice_pk:
        choice = get_object_or_404(Choice, pk=choice_pk)
    else:
        choice = None

    answer = Answer.objects.create(session=session, question=question,
                                   choice=choice)

    unused_questions = session.get_unused_questions()

    if unused_questions.exists():
        question = unused_questions.first()
        question_sequence = session.get_question_sequence(question)
        template = get_template('exams/partials/session-question.html')
        context = {'question': question, 'session': session}
        question_body = template.render(context)

        if choice:
            # FIXME: The field should be `is_right`
            was_right = choice.is_answer
        else:
            was_right = None

        is_marked = utils.is_question_marked(question, session)

        url = question.get_session_url(session)

        return {'done': False,
                "was_right": was_right,
                "is_marked": is_marked,
                'url': url,
                'question_sequence': question_sequence,
                'question_pk': question.pk,
                "question_body": question_body}
    else:
        return {'done': True}

@login_required
@decorators.ajax_only
@csrf.csrf_exempt
def submit_explanation(request):
    question_pk = request.GET.get('question_pk')
    question = get_object_or_404(Question, pk=question_pk)
    latest_revision = question.get_latest_revision()
    context = {'question': question}
    if request.method == 'GET':
        form = forms.ExplanationForm(instance=latest_revision)
    elif request.method == 'POST':
        form = forms.ExplanationForm(request.POST,
                                     instance=latest_revision)
        if form.is_valid():
            form.clone(question, request.user)
            return {}
    context['form'] = form
    return render(request, 'exams/partials/submit_explanation.html', context)


def show_pevious_sessions(request):

    sessions= Session.objects.filter(submitter= request.user)

    return render(request, 'exams/show_previous_sessions.html',{'sesstions':sessions})


class SubjectQuestionCount(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        exam_pk = self.forwarded.get('exam_pk')
        exam = Exam.objects.get(pk=exam_pk)
        qs = exam.subject_set.all()
        if self.q:
            qs = qs.filter(pk=self.q)
        return qs

    def get_result_label(self, item):
        return "<strong>{}</strong> ({})".format(item.name, item.question_set.count())


def show_category_indicators(request, category):
    if not request.user.is_superuser:
        raise PermissionDenied

    context = {'category': category}
    return render(request, 'exams/show_category_indicators.html', context)
