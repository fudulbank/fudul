from dal import autocomplete
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template
from django.utils import timezone
from django.views.decorators import csrf
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST, require_safe
from htmlmin.minify import html_minify
from notifications.models import Notification
from rules.contrib.views import permission_required, objectgetter
from datetime import timedelta
import json

from core import decorators
from teams.models import *
from .models import *
from . import forms, utils, app_rules
import core.utils
import teams.utils


@require_safe
@login_required
def list_meta_categories(request):
    subcategories = Category.objects.meta().user_accessible(request.user)
    context = {'subcategories': subcategories,
               'is_browse_active': True,
    }
    return render(request, 'exams/show_category.html', context)

@require_safe
@login_required
def show_category(request, slugs):
    category = Category.objects.get_from_slugs_or_404(slugs)

    context = {'category': category}

    # PERMISSION CHECK
    if not category.can_user_access(request.user):
        raise PermissionDenied
    subcategories = category.children.user_accessible(request.user)

    # To make sidebar 'active'
    context['is_browse_active'] = True

    if request.user.team_memberships.exists():
        exams = category.exams.filter(privileged_teams__members=request.user).distinct() | category.exams.with_approved_questions()
    else:
        exams = category.exams.with_approved_questions()

    context['exams'] = exams

    # If this category has one child, just go to it!
    if subcategories.count() == 1:
        subcategory = subcategories.first()
        return HttpResponseRedirect(reverse('exams:show_category',
                                            args=(subcategory.get_slugs(),)))

    context.update({
        'subcategories': subcategories.order_by('name'),
    })

    return render(request, "exams/show_category.html", context)

@require_safe
@login_required
def add_question(request, slugs, pk):
    category = Category.objects.get_from_slugs_or_404(slugs)

    # PERMISSION CHECK
    exam = get_object_or_404(Exam, pk=pk, category=category)

    instance = Question(exam=exam)

    context = {'exam': exam,
               'question_form': forms.QuestionForm(instance=instance),
               'revision_form': forms.RevisionForm(),
               'explanation_form': forms.ExplanationForm(is_optional=True),
               'revisionchoiceformset': forms.RevisionChoiceFormset(),
               'is_browse_active': True, # To make sidebar 'active'
    }

    return render(request, "exams/add_question.html", context)


class QuestionAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        exam_pk = self.forwarded.get('exam_pk')
        exam = Exam.objects.get(pk=exam_pk)
        qs = exam.question_set.undeleted()\
                              .order_by_submission()\
                              .filter(child_question__isnull=True)
        if self.q:
            try:
                q = int(self.q)
            except ValueError:
                # If self.q is not an integer
                qs = qs.none()
            else:
                qs = qs.filter(pk=q)
        return qs

    def get_result_label(self, item):
        text_preview = str(item)
        return "<strong>{}</strong>: {}".format(item.pk, text_preview)

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def delete_question(request, pk):
    question_pool = Question.objects.undeleted()\
                                    .select_related('exam',
                                                    'exam__category')
    question = get_object_or_404(question_pool, pk=pk)
    exam = question.exam

    # PERMISSION CHECK
    if not request.user.is_superuser and \
       not exam.can_user_edit(request.user) and \
       not question.is_user_creator(request.user):
        raise Exception("You cannot delete that question!")

    question.is_deleted = True
    question.save()

    return {}

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def handle_question(request, exam_pk, question_pk=None):
    exam = get_object_or_404(Exam.objects.select_related('category'),
                             pk=exam_pk)
    explanation = None
    if question_pk:
        question = get_object_or_404(Question, pk=question_pk,
                                     is_deleted=False)
        revision = question.get_latest_revision()
        explanation = explanation.get_latest_explanation_revision()
    else:
        question = Question(exam=exam)
        revision = Revision(submitter=request.user,
                            is_first=True,
                            is_last=True)

    if not explanation:
        explanation = ExplanationRevision(submitter=request.user,
                                          is_first=True, is_last=True)

    question_form = forms.QuestionForm(request.POST,
                                       instance=question)
    revision_form = forms.RevisionForm(request.POST,
                                       request.FILES,
                                       instance=revision)
    revisionchoiceformset = forms.RevisionChoiceFormset(request.POST,
                                                        instance=revision)
    explanation_form = forms.ExplanationForm(request.POST,
                                             request.FILES,
                                             instance=explanation,
                                             is_optional=True)

    if question_form.is_valid() and \
       revision_form.is_valid() and \
       explanation_form.is_valid() and \
       revisionchoiceformset.is_valid():
        question = question_form.save()
        revision = revision_form.save(commit=False)
        revision.question = question
        revision.is_contribution = not teams.utils.is_editor(request.user)
        revision.save()
        revision_form.save_m2m()

        revisionchoiceformset.instance = revision
        revisionchoiceformset.save()

        # This test relies on choices, so the choices have to be saved
        # before
        revision.is_approved = utils.test_revision_approval(revision)
        revision.save()

        explanation = explanation_form.save(commit=False)
        if explanation:
            explanation.is_contribution = not teams.utils.is_editor(request.user)
            explanation.question = question
            explanation.save()

        question.best_revision = revision
        question.update_is_approved()
        question.save()

        show_url = reverse('exams:approve_user_contributions', args=(exam.category.get_slugs(), exam.pk))
        return {"question_pk": question.pk,
                "show_url": show_url}

    context = {'exam': exam,
               'question_form': question_form,
               'revision_form': revision_form,
               'explanation_form': explanation_form,
               'revisionchoiceformset': revisionchoiceformset}

    return render(request, "exams/partials/question_form.html", context)

@require_safe
@decorators.ajax_only
@login_required
def update_exam_stats(request, pk):
    exam = get_object_or_404(Exam, pk=pk)

    # PERMISSION CHECK
    if not exam.can_user_access(request.user):
        raise PermissionDenied

    template = get_template('exams/partials/exam_stats.html')
    context = {'exam': exam}
    stat_html = template.render(context)

    return {"stat_html": stat_html}

@require_safe
@login_required
def list_questions(request, slugs, pk, selector=None):
    category = Category.objects.get_from_slugs_or_404(slugs)

    exam = get_object_or_404(Exam.objects.select_related('category'), pk=pk, category=category)
    assignment_form = forms.AssignQuestionForm(exam=exam)

    # PERMISSION CHECK
    if not exam.can_user_access(request.user):
        raise PermissionDenied

    context = {'exam': exam,
               'category_slugs': slugs,
               'selector': selector,
               'assignment_form': assignment_form,
               'is_browse_active': True}

    if selector:
        if selector.startswith('i-'):
            issue_pk = int(selector[2:])
            issue = get_object_or_404(Issue, pk=issue_pk)
            context['list_name'] = issue.name
        elif selector.startswith('s-'):
            subject_pk = int(selector[2:])
            subject = get_object_or_404(exam.subject_set, pk=subject_pk)
            context['list_name'] = subject.name
        elif selector == 'all':
            context['list_name'] = "all questions"
        elif selector == 'no_answer':
            context['list_name'] = "no right answers"
        elif selector == 'no_issues':
            context['list_name'] = "no issues"
        elif selector == 'blocking_issues':
            context['list_name'] = "blocking issues"
        elif selector == 'nonblocking_issues':
            context['list_name'] = "non-blocking issues"
        elif selector == 'approved':
            context['list_name'] = "approved latesting revision"
        elif selector == 'pending':
            context['list_name'] = "pending latesting revision"
        elif selector == 'lacking_choices':
            context['list_name'] = "lacking choices"
        else:
            raise Http404
        return render(request, 'exams/list_questions_by_selector.html', context)
    else: # if no selector
        context['issues'] = Issue.objects.all()
        return render(request, 'exams/list_questions_index.html', context)

@login_required
@require_safe
@decorators.ajax_only
def show_question(request, pk, revision_pk=None):

    question = get_object_or_404(Question.objects.select_related('exam'),
                                 pk=pk,
                                 is_deleted=False)
    if revision_pk:
        revision = get_object_or_404(Revision, pk=revision_pk)
        explanation_revision = None
    else:
        revision = question.get_best_revision()
        explanation_revision = question.get_latest_explanation_revision()

    # PERMISSION CHECK
    if not question.exam.can_user_access(request.user):
        raise PermissionDenied

    context = {'revision': revision,
               'explanation_revision': explanation_revision}
    return render(request, 'exams/partials/show_question.html', context)

@login_required
@require_safe
@decorators.ajax_only
def show_explanation_revision(request, pk):
    explanation_pool = ExplanationRevision.objects.undeleted()\
                                                  .select_related('question',
                                                                  'question__exam',
                                                                  'question__exam__category')
    explanation_revision = get_object_or_404(explanation_pool, pk=pk)
    exam = explanation_revision.question.exam

    # PERMISSION CHECK
    if not exam.can_user_access(request.user):
        raise PermissionDenied

    context = {'explanation_revision': explanation_revision}
    return render(request, 'exams/partials/show_explanation.html', context)

@require_safe
@login_required
def list_revisions(request, slugs, exam_pk, pk):
    # PERMISSION CHECK
    category = Category.objects.get_from_slugs_or_404(slugs)
    if not category.can_user_access(request.user):
        raise PermissionDenied

    question = get_object_or_404(Question.objects.select_related('exam',
                                                                 'exam__category'),
                                 pk=pk,
                                 is_deleted=False)
    context = {'question': question,
               'is_browse_active': True,
               'exam': question.exam}
    return render(request, 'exams/list_revisions.html', context)

@login_required
def submit_revision(request, slugs, exam_pk, pk):
    category = Category.objects.get_from_slugs_or_404(slugs)

    exam = get_object_or_404(Exam, pk=exam_pk, category=category)
    question = get_object_or_404(Question, pk=pk, is_deleted=False)
    #TODO :latest approved revision
    latest_revision = question.get_latest_revision()
    latest_explanation_revision = question.get_latest_explanation_revision()

    # PERMISSION CHECK
    # if not exam.can_user_edit(request.user):
    #     raise PermissionDenied
    context = {'exam': exam, 'revision': latest_revision}

    if request.method == 'POST':
        question_form = forms.QuestionForm(request.POST,
                                          instance=question)
        revision_form = forms.RevisionForm(request.POST,
                                          request.FILES,
                                          instance=latest_revision)
        explanation_form = forms.ExplanationForm(request.POST,
                                                 request.FILES,
                                                 instance=latest_explanation_revision,
                                                 is_optional=True)

        revisionchoiceformset = forms.RevisionChoiceFormset(request.POST,
                                                            instance=latest_revision)
        if question_form.is_valid() and \
           revision_form.is_valid() and \
           explanation_form.is_valid() and \
           revisionchoiceformset.is_valid():
            question = question_form.save()
            new_revision = revision_form.clone(question, request.user)
            explanation_form.clone(question, request.user)
            revisionchoiceformset.clone(new_revision)

            # This test relies on choices, so the choices have to be saved
            # before.
            new_revision.is_approved = utils.test_revision_approval(new_revision)
            new_revision.save()
            question.update_is_approved()
            question.save()

            return HttpResponseRedirect(
                reverse("exams:list_revisions",
                        args=(slugs, exam_pk, pk)))

    elif request.method == 'GET':
        question_form = forms.QuestionForm(instance=question)
        revision_form = forms.RevisionForm(instance=latest_revision)
        explanation_form = forms.ExplanationForm(instance=latest_explanation_revision,
                                                 is_optional=True)
        revisionchoiceformset = forms.RevisionChoiceFormset(instance=latest_revision)
    context['question_form'] = question_form
    context['revision_form'] = revision_form
    context['explanation_form'] = explanation_form
    context['revisionchoiceformset'] = revisionchoiceformset

    return render(request, 'exams/submit_revision.html', context)

@login_required
def create_session(request, slugs, exam_pk):
    category = Category.objects.get_from_slugs_or_404(slugs)

    exam = get_object_or_404(Exam, pk=exam_pk, category=category)

    # PERMISSION CHECK
    if not category.can_user_access(request.user):
        raise PermissionDenied

    if not exam.was_announced and \
       not exam.can_user_edit(request.user):
        return render(request, "exams/coming_soon.html", {'exam': exam})

    # If the exam has no approved questions, it doesn't exist for
    # users.
    if not exam.can_user_edit(request.user) and \
       not exam.question_set.undeleted().exists():
        raise Http404

    latest_sessions = exam.session_set.undeleted()\
                                      .filter(submitter=request.user)\
                                      .order_by('-pk')[:10]

    question_count = exam.question_set.approved().count()
    context = {'exam': exam,
               'question_count': question_count,
               'latest_sessions': latest_sessions,
               'is_browse_active': True, # To make sidebar 'active'
    }

    if request.method == 'GET':
        sessionform = forms.SessionForm(exam=exam, user=request.user)
    elif request.method == 'POST':
        instance = Session(submitter=request.user, exam=exam)
        sessionform = forms.SessionForm(request.POST,
                                        instance=instance, exam=exam,
                                        user=request.user)
        if sessionform.is_valid():
            # Question allocation happens in SessionForm.save()
            session = sessionform.save()
            return HttpResponseRedirect(reverse("exams:show_session",
                                                args=(slugs, exam_pk, session.pk)))
    context['sessionform'] = sessionform

    return render(request, "exams/create_session.html", context)

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def create_session_automatically(request, slugs, exam_pk):
    category = Category.objects.get_from_slugs_or_404(slugs)
    exam = get_object_or_404(Exam, pk=exam_pk, category=category)

    is_shared = request.POST.get('is_shared', False)
    selector = request.POST.get('selector')
    session_pk = request.POST.get('session_pk')
    subject_pk = request.POST.get('subject_pk')

    if not selector or selector not in ['ALL', 'SKIPPED', 'INCORRECT']:
        return HttpResponseBadRequest()

    if subject_pk:
        subject = get_object_or_404(Subject, pk=subject_pk, exam=exam)
    else:
        subject = None

    if session_pk:
        original_session = get_object_or_404(Session, pk=session_pk,
                                             exam=exam)
    else:
        original_session = None    

    # PERMISSION CHECK
    if not category.can_user_access(request.user) or \
       original_session and not is_shared and not request.user.has_perm('exams.access_session', original_session):
        raise Exception("You are not allowed to create such a session.")

    # DO NOT FUCK WITH US
    if not exam.was_announced and \
       not exam.can_user_edit(request.user):
        return render(request, "exams/coming_soon.html", {'exam': exam})

    instance = Session(exam=exam,
                       submitter=request.user)

    if is_shared:
        instance.parent_session = original_session
        session_mode = original_session.session_mode
    else:
        session_mode = 'EXPLAINED'

    data = {'session_mode': session_mode,
            'question_filter': selector}
    if subject:
        data['subjects'] = [subject_pk]

    form = forms.SessionForm(data, exam=exam, user=request.user,
                             original_session=original_session,
                             instance=instance, is_automatic=True)
    form.is_valid()
    session = form.save()

    return {'url': session.get_absolute_url()}

@login_required
@require_safe
@permission_required('exams.access_exam', fn=objectgetter(Exam, 'exam_pk'), raise_exception=True)
@cache_page(settings.CACHE_PERIODS['EXPENSIVE_UNCHANGEABLE'])
@decorators.ajax_only
def list_partial_session_questions(request, slugs, exam_pk):
    try:
        pks = [int(pk) for pk in request.GET.get('pks', '').split(',')]
    except ValueError:
        return HttpResponseBadRequest('No valid "pks" parameter was provided')

    questions = Question.objects.select_related('best_revision', 'exam')\
                                .filter(exam__pk=exam_pk, pk__in=pks)
    template = get_template("exams/partials/partial_session_question_list.html")
    context = {'questions': questions, 'user': request.user}
    html = template.render(context)
    minified_html = html_minify(html)

    return {'html': minified_html}

@require_safe
def show_single_question(request, slugs, exam_pk, question_pk):
    category = Category.objects.get_from_slugs_or_404(slugs)
    current_question = get_object_or_404(Question.objects.select_related('best_revision', 'exam')\
                                                         .undeleted(),
                                         pk=question_pk)
    context = {'category_slugs': slugs,
              'default_session_theme': SessionTheme.objects.get(name="Ocean"),
               'current_question': current_question}
    return render(request, "exams/show_question.html", context)

@login_required
@require_safe
#@cache_page(settings.CACHE_PERIODS['STABLE'])
def show_session(request, slugs, exam_pk, session_pk, question_pk=None):
    category = Category.objects.get_from_slugs_or_404(slugs)
    session = get_object_or_404(Session.objects.select_related('parent_session',
                                                               'parent_session__submitter',
                                                               'exam',
                                                               'exam__category')\
                                               .undeleted(),
                                pk=session_pk)


    # If the user has no access to the session, direct them to the
    # question.
    if not session.can_user_access(request.user):
        if question_pk:
            url = reverse('exams:show_single_question', args=(slugs, exam_pk, question_pk))
            return HttpResponseRedirect(url)
        else:
            raise PermissionDenied

    current_question = session.get_current_question(question_pk)
    session_questions = session.get_questions().values_list('pk', 'global_sequence')
    # This produces a dictionary of keys being question_pks and values
    # being global_sequences
    session_question_pks = json.dumps(dict(session_questions))

    shared_sessions = Session.objects.get_shared(session)
    context = {'session': session,
               'is_shared': shared_sessions.exists(),
               'shared_sessions': shared_sessions,
               'default_session_theme': SessionTheme.objects.get(name="Ocean"),
               'session_themes': SessionTheme.objects.all(),
               'category_slugs': slugs,
               'current_question': current_question,
               'session_question_pks': session_question_pks}

    return render(request, "exams/show_session.html", context)

@require_safe
@login_required
@permission_required('exams.access_session', fn=objectgetter(Session, 'session_pk'), raise_exception=True)
def show_session_results(request, slugs, exam_pk, session_pk):
    category = Category.objects.get_from_slugs_or_404(slugs)

    session = get_object_or_404(Session.objects.undeleted()\
                                               .select_related('exam', 'submitter')\
                                               .exclude(session_mode__in=['INCOMPLETE', 'SOLVED']),
                                pk=session_pk)

    if not session.has_finished and \
       request.user == session.submitter:
        answers = []
        for question in session.get_unused_questions():
            answer = Answer(session=session, question=question)
            answers.append(answer)
        Answer.objects.bulk_create(answers)
        session.set_has_finished()

    # We don't use the standard QuerySets as they don't filter per a
    # specific session.
    context = {'session': session, 'exam': session.exam,
               'category_slugs': slugs,
               'skipped_count': session.get_skipped_count(),
               'correct_count': session.get_correct_count(),
               'incorrect_count': session.get_incorrect_count()
    }

    return render(request, 'exams/show_session_results.html', context)

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def toggle_marked(request):
    question_pk = request.POST.get('question_pk')
    session_pk = request.POST.get('session_pk')
    question = get_object_or_404(Question.objects.undeleted().select_related('exam'),
                                 pk=question_pk)

    # PERMISSION CHECKS
    if session_pk:
        session = get_object_or_404(Session.objects.select_related('submitter')\
                                                   .undeleted(),
                            pk=session_pk)
        if not session.submitter == request.user:
            raise Exception("You cannot mark questions in this session.")
    elif not session_pk and not question.exam.can_user_access(request.user):
        raise Exception("You cannot mark questions in this exam.")

    if utils.is_question_marked(question, request.user):
        question.marking_users.remove(request.user)
        is_marked = False
    else:
        question.marking_users.add(request.user)
        is_marked = True

    return {'is_marked': is_marked}

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def submit_highlight(request):
    session_pk = request.POST.get('session_pk')
    session = get_object_or_404(Session.objects.select_related('submitter')\
                                               .undeleted(),
                                pk=session_pk)

    # PERMISSION CHECKS
    if not session.submitter == request.user:
        raise Exception("You cannot highlight a question in this session.")

    best_revision_pk = request.POST.get('best_revision_pk')
    best_revision = get_object_or_404(Revision.objects.select_related('question'),
                                      pk=best_revision_pk)
    stricken_choice_pks = request.POST.get('stricken_choice_pks', '[]')
    stricken_choice_pks = json.loads(stricken_choice_pks)
    stricken_choices = Choice.objects.filter(pk__in=stricken_choice_pks)
    highlighted_text = request.POST.get('highlighted_text', '')

    highlight, was_created = Highlight.objects.get_or_create(session=session,
                                                             question=best_revision.question,
                                                             defaults={'revision': best_revision})

    highlight.revision = best_revision

    if not '<span ' in highlighted_text:
        highlighted_text = ""

    highlight.highlighted_text = highlighted_text
    highlight.save()

    highlight.stricken_choices = stricken_choices

    return {}

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def submit_answer(request):
    question_pk = request.POST.get('question_pk')
    session_pk = request.POST.get('session_pk')
    choice_pk = request.POST.get('choice_pk')
    session = get_object_or_404(Session.objects.select_related('submitter').undeleted(), pk=session_pk)
    question = get_object_or_404(session.get_questions(), pk=question_pk)

    # PERMISSION CHECKS
    if not session.submitter == request.user:
        raise Exception("You cannot submit answers in this session")
    if question.was_solved_in_session(session):
        raise Exception("Question #{} was previously solved in this session.".format(question_pk))

    if choice_pk:
        choice = get_object_or_404(Choice, pk=choice_pk)
    else:
        choice = None

    answer = Answer.objects.create(session=session, question=question,
                                   choice=choice)
    session.set_has_finished()

    return {}

@require_safe
@login_required
def list_previous_sessions(request):
    sessions = request.user.session_set\
                           .select_related('exam', 'exam__category')\
                           .undeleted()\

    context = {'sessions':sessions,
               'is_previous_active': True}

    return render(request, 'exams/list_previous_sessions.html',
                  context)

@login_required
@decorators.ajax_only
@csrf.csrf_exempt
def contribute_explanation(request):
    question_pk = request.GET.get('question_pk')
    question = get_object_or_404(Question, pk=question_pk,
                                 is_deleted=False)
    instance = question.get_latest_explanation_revision()

    if request.method == 'GET':
        form = forms.ExplanationForm(instance=instance)

    elif request.method == 'POST':
        if not instance:
            instance = ExplanationRevision(question=question,
                                           submitter=request.user)
        form = forms.ExplanationForm(request.POST,
                                     request.FILES,
                                     instance=instance)
        if form.is_valid():
            new_explanation = form.clone(question, request.user)

            template = get_template('exams/partials/show_explanation.html')
            context = {'explanation_revision': new_explanation}
            explanation_html = template.render(context)
            return {'explanation_html': explanation_html}

    context = {'question': question,
               'form': form}
    return render(request, 'exams/partials/contribute_explanation.html', context)

@login_required
@decorators.ajax_only
@csrf.csrf_exempt
def contribute_revision(request):
    question_pk = request.GET.get('question_pk')
    question = get_object_or_404(Question.objects.undeleted(),
                                 pk=question_pk)
    latest_revision = question.get_latest_revision()

    if request.method == 'GET':
        revision_initial = {'change_summary': ''}
        revision_form = forms.RevisionForm(instance=latest_revision, initial=revision_initial)
        revisionchoiceformset = forms.ContributedRevisionChoiceFormset(instance=latest_revision)
    elif request.method == 'POST':
        revision_form = forms.RevisionForm(request.POST,
                                          request.FILES,
                                          instance=latest_revision)

        revisionchoiceformset = forms.ContributedRevisionChoiceFormset(request.POST,
                                                            instance=latest_revision)
        if revision_form.is_valid() and \
           revisionchoiceformset.is_valid():
            new_revision = revision_form.clone(question,request.user)
            choices = revisionchoiceformset.clone(new_revision)

            new_revision.is_contribution = not teams.utils.is_editor(request.user)
            new_revision.save()
            revision_form.save_m2m()

            # This test relies on choices, so the choices have to be saved
            # before.
            new_revision.is_approved = utils.test_revision_approval(new_revision)
            new_revision.save()
            question.update_is_approved()
            question.save()
            return {}

    context = {'question': question,
               'revision_form': revision_form,
               'revisionchoiceformset': revisionchoiceformset}

    return render(request, 'exams/partials/contribute_revision.html', context)

@login_required
def approve_user_contributions(request,slugs,exam_pk):

    category = Category.objects.get_from_slugs_or_404(slugs)

    exam = get_object_or_404(Exam, pk=exam_pk, category=category)

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied
    pks = utils.get_contributed_questions(exam).values_list('pk', flat=True)
    revisions = Revision.objects.per_exam(exam).filter(is_contribution=True,is_deleted=False,is_approved=False).exclude(question__pk__in=pks)
    contributed_questions = utils.get_contributed_questions(exam)
    number_of_contributions = Revision.objects.filter(submitter=request.user).count()

    context ={'revisions':revisions,'contributed_questions':contributed_questions,'number_of_contributions':number_of_contributions,'exam':exam}
    return render(request, 'exams/approve_user_contributions.html',context)

# COMPAIN WITH SHOW_QUESTION IF NO FURTHER CHANGE IS DONE
@login_required
@decorators.ajax_only
def show_revision_comparison(request, pk, review=False):
    revision = get_object_or_404(Revision.objects.select_related('question',
                                                                 'question__exam',
                                                                 'question__exam__category'),
                                 pk=pk, is_deleted=False)

    # PERMISSION CHECK
    if not revision.question.exam.can_user_access(request.user):
        raise PermissionDenied

    context = {'revision': revision,
               'review': bool(review)}
    return render(request, 'exams/partials/show_revision_comparison.html', context)

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def delete_revision(request, pk):
    revision_pool = Revision.objects.undeleted()\
                                    .select_related('question',
                                                    'question__exam',
                                                    'question__exam__category')
    revision = get_object_or_404(revision_pool, pk=pk)
    question = revision.question
    exam = question.exam

    # PERMISSION CHECK
    if not request.user.is_superuser and \
       not exam.can_user_edit(request.user) and \
       not revision.submitter == request.user:
        raise Exception("You cannot delete this revision!")

    revision.is_deleted = True
    revision.save()

    # If no undeleted revision remains, then mark the whole question
    # as deleted as well.
    if not question.revision_set.undeleted().count():
        question.is_deleted = True
        question.save()
    else:
        # Mark the new last revision as such
        question.update_latest()
        question.update_best_revision()
        question.update_is_approved()
        question.save()

    return {}

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def delete_explanation_revision(request, pk):
    explanation_pool = ExplanationRevision.objects.undeleted()\
                                                  .select_related('submitter',
                                                                  'question',
                                                                  'question__exam',
                                                                  'question__exam__category')
    explanation_revision = get_object_or_404(explanation_pool, pk=pk)
    question = explanation_revision.question
    exam = question.exam

    # PERMISSION CHECK
    if not request.user.is_superuser and \
       not exam.can_user_edit(request.user) and \
       not explanation_revision.submitter == request.user:
        raise Exception("You cannot delete this explanation!")

    explanation_revision.is_deleted = True
    explanation_revision.save()

    # Mark the new last explanation as such
    question.update_latest()

    return {}

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def mark_revision_approved(request, pk):
    revision_pool = Revision.objects.undeleted()\
                                    .select_related('question',
                                                    'question__exam')
    revision = get_object_or_404(revision_pool, pk=pk)
    question = revision.question
    exam = revision.question.exam

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise Exception("You cannot change the approval status.")


    revision.is_approved = True
    revision.approved_by= request.user
    revision.save()

    question.update_best_revision()
    question.update_is_approved()
    question.save()

    return {}

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def mark_revision_pending(request, pk):
    revision_pool = Revision.objects.undeleted()\
                                    .select_related('question',
                                                    'question__exam')
    revision = get_object_or_404(revision_pool, pk=pk)
    question = revision.question
    exam = revision.question.exam

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise Exception("You cannot change the approval status.")

    revision.is_approved = False
    revision.approved_by= request.user
    revision.save()

    question.update_best_revision()
    question.update_is_approved()
    question.save()

    return {}

@login_required
def approve_question(request, slugs, exam_pk, pk):
    category = Category.objects.get_from_slugs_or_404(slugs)

    # PERMISSION CHECK
    exam = get_object_or_404(Exam, pk=exam_pk, category=category)
    question = get_object_or_404(Question, pk=pk)
    revision = question.get_latest_revision()
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    editor = exam.can_user_edit(request.user)

    context = {'exam': exam,
               'question_form': forms.QuestionForm(instance=question),
               'revision_form': forms.RevisionForm(instance=revision),
               'revisionchoiceformset': forms.RevisionChoiceFormset(instance=revision),
               'question': question}

    return render(request, "exams/add_question.html", context)

@require_safe
@login_required
def show_my_performance(request):
    user_question_pks = Answer.objects.filter(session__submitter=request.user,
                                              session__is_deleted=False)\
                                      .values('question')
    user_questions = Question.objects.undeleted()\
                                     .filter(pk__in=user_question_pks)
    total_questions = user_questions.count()
    correct_count = Question.objects.correct_by_user(request.user)\
                                    .count()
    incorrect_count = Question.objects.incorrect_by_user(request.user)\
                                      .count()
    skipped_count = Question.objects.skipped_by_user(request.user)\
                                    .count()

    # Only get exams which the user has taken
    exams = Exam.objects.select_related('category')\
                        .filter(session__submitter=request.user,
                                session__is_deleted=False,
                                session__answer__isnull=False).distinct()

    context = {'correct_count': correct_count,
               'incorrect_count': incorrect_count,
               'skipped_count': skipped_count,
               'exams': exams,
               'is_performance_active': True}

    return render(request, "exams/show_my_performance.html", context)

@login_required
@require_safe
def show_my_performance_per_exam(request, exam_pk):
    user_exams = Exam.objects.filter(session__submitter=request.user,
                                     session__is_deleted=False)\
                             .distinct()
    exam = get_object_or_404(user_exams, pk=exam_pk)
    correct_count =  utils.get_user_question_stats(target=exam,
                                                       user=request.user,
                                                       result='correct')
    incorrect_count =  utils.get_user_question_stats(target=exam,
                                                         user=request.user,
                                                         result='incorrect')
    skipped_count =  utils.get_user_question_stats(target=exam,
                                                       user=request.user,
                                                       result='skipped')
    context = {'correct_count': correct_count,
               'incorrect_count': incorrect_count,
               'skipped_count': skipped_count,
               'exam': exam,
               'is_performance_active': True}

    return render(request, "exams/show_my_performance_per_exam.html", context)

@login_required
@require_safe
def show_credits(request,pk):
    exam = get_object_or_404(Exam, pk=pk)

    # PERMISSION CHECK
    if not exam.can_user_access(request.user):
        raise PermissionDenied

    return render(request, 'exams/partials/show_credits.html',{'exam':exam})

@login_required
@require_safe
def list_contributions(request,user_pk=None):
    # PERMISSION CHECK
    # No need.  Similar to list_revisions

    if user_pk:
        contributor = get_object_or_404(User,pk=user_pk)
    else:
        contributor = request.user

    revisions = Revision.objects.select_related('question',
                                                'question__exam',
                                                'question__exam__category')\
                                .undeleted()\
                                .filter(submitter=contributor)\
                                .order_by('-submission_date')
    context = {'revisions':revisions, 'contributor': contributor}

    return render(request, 'exams/list_contributions.html', context)

@require_safe
@login_required
def search(request):
    q = request.GET.get('q')
    categories= utils.get_user_allowed_categories(request.user)
    #TODO:try to add choices to search
    if q:
        search_fields =['pk','best_revision__text','best_revision__choice__text']
        if teams.utils.is_editor(request.user):
            qs = Question.objects.filter(exam__category__in=categories,
                                         best_revision__is_last=True)\
                                 .distinct()
        else:
            qs = Question.objects.undeleted()\
                                 .filter(exam__category__in=categories,
                                         best_revision__is_last=True,
                                         best_revision__is_approved=True)\
                                 .distinct()
        questions = core.utils.get_search_queryset(qs, search_fields, q)
        return render(request, 'exams/search_results.html', {'questions': questions, 'query': q})
    return render(request, 'exams/search_results.html', {'search': True})


@login_required
@decorators.ajax_only
@csrf.csrf_exempt
def correct_answer(request):
    action = request.POST.get('action')
    choice_pk = request.GET.get('choice_pk')
    changed = False

    # PERMISSION CHECK
    choice_pool = Choice.objects.filter(revision__question__session__submitter=request.user)\
                                .select_related('revision',
                                                'revision__question',
                                                'revision__question__exam')\
                                .distinct()
    choice = get_object_or_404(choice_pool, pk=choice_pk,
                               revision__is_deleted=False,
                               revision__question__is_deleted=False)
    if not choice.revision.question.exam.can_user_access(request.user):
        raise PermissionDenied

    if request.method == 'GET':
        form = forms.AnswerCorrectionForm()
    elif request.method == 'POST':
        correction = AnswerCorrection.objects.select_related('submitter').filter(choice=choice).first()
        if correction:
            if correction.submitter == request.user:
                raise Exception("You were the one that submitted this correction, so you cannot vote.")

            if action in ['add', 'support']:
                if correction.supporting_users.filter(pk=request.user.pk).exists():
                    raise Exception("You have already supported this correction.")
                elif correction.opposing_users.filter(pk=request.user.pk).exists():
                    correction.opposing_users.remove(request.user)
                correction.supporting_users.add(request.user)
                correction.notify_submitter(request.user)
            elif action == 'oppose':
                if correction.opposing_users.filter(pk=request.user.pk).exists():
                    raise Exception("You have already opposed this correction.")
                elif correction.supporting_users.filter(pk=request.user.pk).exists():
                    correction.supporting_users.remove(request.user)
                    correction.unnotify_submitter(request.user)
                correction.opposing_users.add(request.user)
            else:
                return HttpResponseBadRequest()
            changed = True
        else:
            instance = AnswerCorrection(submitter=request.user,
                                        choice=choice)
            form = forms.AnswerCorrectionForm(request.POST,
                                              instance=instance)
            if form.is_valid():
                form.save()
                changed = True

    if changed:
        template = get_template('exams/partials/show_answer_correction.html')
        context = {'choice': choice, 'user': request.user}
        correction_html = template.render(context)
        return {'correction_html': correction_html}
    else:
        context = {'choice': choice, 'form': form}
        return render(request, 'exams/partials/correct_answer.html', context)

@login_required
@decorators.ajax_only
@csrf.csrf_exempt
def delete_correction(request):
    choice_pk = request.GET.get('choice_pk')
    correction = get_object_or_404(AnswerCorrection.objects.select_related('choice'), choice__pk=choice_pk)

    # PERMISSION CHECK
    if not correction.can_user_delete(request.user):
        raise PermissionDenied

    new_submitter = correction.supporting_users.first()
    if new_submitter:
        correction.submitter = new_submitter
        correction.save()
        correction.supporting_users.remove(new_submitter)
        template = get_template('exams/partials/show_answer_correction.html')
        context = {'choice': correction.choice, 'user': request.user}
        correction_html = template.render(context)
        return {'correction_html': correction_html}
    else:
        correction.delete()
        return {'correction_html': None}

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def get_selected_question_count(request, exam_pk):
    exam = get_object_or_404(Exam, pk=exam_pk)

    # PERMISSION CHECK
    if not exam.can_user_access(request.user):
        raise PermissionDenied

    form = forms.SessionForm(request.POST,
                             user=request.user,
                             exam=exam)
    form.full_clean()

    question_filter = form.cleaned_data.get('question_filter')
    if question_filter:
        question_pool = form.question_pools[question_filter]
    else:
        question_pool = form.question_pools['ALL']

    subjects = form.cleaned_data.get('subjects')
    if subjects:
        question_pool = question_pool.filter(subjects__in=subjects)

    sources = form.cleaned_data.get('sources')
    if sources:
        question_pool = question_pool.filter(sources__in=sources)

    exam_types = form.cleaned_data.get('exam_types')
    if exam_types:
        question_pool = question_pool.filter(exam_types__in=exam_types)

    return {'count': question_pool.count()}

@login_required
@require_POST
@csrf.csrf_exempt
@decorators.ajax_only
def delete_session(request):
    if not 'deletion_type' in request.POST:
        return HttpResponseBadRequest()
    deletion_type = request.POST['deletion_type']

    if deletion_type == 'all':
        request.user.session_set.update(is_deleted=True)
        request.user.marked_questions.clear()
    elif deletion_type == 'exam':
        exam_pk = request.POST.get('pk')
        exam = Exam.objects.get(pk=exam_pk)
        request.user.session_set.filter(exam=exam).update(is_deleted=True)
        questions_to_unmark = request.user.marked_questions\
                                          .filter(exam=exam)
        request.user.marked_questions.remove(*questions_to_unmark)
    elif deletion_type == 'session':
        session_pk = request.POST.get('pk')
        session = Session.objects.select_related('submitter')\
                                 .get(pk=session_pk)

        # PERMISSION CHECK
        if session.submitter != request.user:
            raise Exception("You cannot ask for forgiveness for this session.")

        session.is_deleted = True
        session.save()

        # Unmark questions that are only in this session.
        other_user_sessions = Session.objects.filter(submitter=request.user)\
                                             .exclude(pk=session_pk)
        questions_to_unmark = request.user.marked_questions\
                                          .filter(session=session)\
                                          .exclude(session__in=other_user_sessions)
        request.user.marked_questions.remove(*questions_to_unmark)

    return {}

@csrf.csrf_exempt
@require_safe
@decorators.ajax_only
def count_answers(request):
    return {'answer_count': Answer.objects\
                                  .filter(choice__isnull=False)\
                                  .count()
            }

@csrf.csrf_exempt
@require_safe
@decorators.ajax_only
def get_correct_percentage(request):
    correct_percentage = utils.get_correct_percentage()
    return {'correct_percentage': correct_percentage}

@login_required
@decorators.ajax_only
@csrf.csrf_exempt
def contribute_mnemonics(request):
    action = request.POST.get('action')
    question_pk = request.GET.get('question_pk')
    question = get_object_or_404(Question.objects.select_related('exam'),
                                 pk=question_pk,
                                 is_deleted=False)
    exam = question.exam
    mnemonics = question.mnemonic_set.filter(is_deleted=False)

    if request.method == 'GET':
        form = forms.ContributeMnemonic()
    elif request.method == 'POST':
        if action in ['add']:
            instance = Mnemonic(submitter=request.user,
                                question=question)
            form = forms.ContributeMnemonic(request.POST, request.FILES,
                                            instance=instance)
            if form.is_valid():
                form.save()
                template = get_template('exams/partials/show_mnemonics.html')
                context = {'question': question,'user':request.user}
                mnemonic_html = template.render(context)
                return {'mnemonic_html':mnemonic_html}
        elif Mnemonic.objects.filter(question=question).exists():
            mnemonic_pk = request.POST.get('mnemonic_pk')
            mnemonic = get_object_or_404(Mnemonic.objects.select_related('submitter'), pk=mnemonic_pk)
            if action == 'like':
                if mnemonic.submitter == request.user:
                    raise Exception("You were the one that submitted this mnemonic, so you cannot vote.")

                if mnemonic.likes.filter(pk=request.user.pk).exists():
                    raise Exception("You have already liked this mnemonic.")
                mnemonic.likes.add(request.user)
                mnemonic.notify_submitter(request.user)
                template = get_template('exams/partials/show_mnemonics.html')
                context = {'question': question,'user':request.user}
                mnemonic_html = template.render(context)
                return {'mnemonic_html':mnemonic_html}

            elif action == 'delete':
                if not request.user.is_superuser and \
                   not exam.can_user_edit(request.user) and \
                   not mnemonic.submitter == request.user:
                    raise Exception("You cannot delete this mnemonic!")

                mnemonic.is_deleted = True
                mnemonic.save()
                Notification.objects.filter(verb='mnemonic').delete()
                template = get_template('exams/partials/show_mnemonics.html')
                context = {'question': question,'user':request.user, 'exam':exam}
                mnemonic_html = template.render(context)
                return {'mnemonic_html':mnemonic_html}

            else:
                return HttpResponseBadRequest()
        else:
            return HttpResponseBadRequest()

    context = {'question': question, 'form': form, 'mnemonics':mnemonics, 'exam':exam}
    return render(request, 'exams/partials/contribute_mnemonics.html', context)

@login_required
@require_POST
@decorators.ajax_only
@csrf.csrf_exempt
def assign_questions(request):
    try:
        pks = [int(pk) for pk in request.POST.get('pks').split(',')]
    except TypeError:
        return HttpResponseBadRequest('No valid "pks" parameter was provided')

    clear = request.POST.get('clear')
    if clear == 'true':
        assigned_editor = None
    elif clear == 'false':
        editor_pk = request.POST.get('editor_pk')
        assigned_editor = User.objects.get(pk=editor_pk)

    questions = Question.objects.filter(pk__in=pks)
    questions.update(assigned_editor=assigned_editor)
    return {}


@login_required
@require_safe
def list_assigned_questions(request):
    return render(request, 'exams/list_assigned_questions.html')

@login_required
@require_safe
def list_duplicates(request, slugs, pk):
    exam = get_object_or_404(Exam, pk=pk)

    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    duplicate_containers = exam.get_pending_duplicates()

    context = {'exam': exam, 'duplicate_containers': duplicate_containers,
               'category_slugs': slugs}
    return render(request, 'exams/list_duplicates.html', context)

@login_required
@require_POST
@decorators.ajax_only
@csrf.csrf_exempt
def handle_duplicate(request):
    question_pk = request.POST.get('question_pk')
    container_pk = request.POST.get('container_pk')
    action = request.POST.get('action')

    container = get_object_or_404(DuplicateContainer.objects.select_related('primary_question',
                                                                            'primary_question__exam'),
                                  pk=container_pk,
                                  status="PENDING")

    if not container.primary_question.exam.can_user_edit(request.user):
        raise PermissionDenied

    if action == 'keep':
        question_to_keep = get_object_or_404(Question.objects.select_related('best_revision'),
                                             pk=question_pk)
        container.keep(question_to_keep)
        container.status = 'KEPT'
    elif action == 'decline':
        container.status = 'DECLINED'

    container.reviser = request.user
    container.revision_date = timezone.now()
    container.save()

    return {}

@login_required
@require_safe
def show_tool_index(request):
    if request.user.is_superuser:
        privileged_exams = Exam.objects.all()
    else:
        privileged_exams = Exam.objects.filter(privileged_teams__members=request.user)
    context = {'privileged_exams': privileged_exams}

    return render(request, 'exams/show_tool_index.html', context)

@login_required
@require_safe
def list_suggestions(request, slugs, pk):
    exam = get_object_or_404(Exam.objects.select_related('category',
                                                         'category__parent_category'),
                             pk=pk)

    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context = {'exam': exam, 'category_slugs': slugs,
               'pending_count': exam.get_pending_suggested_changes().count()}

    return render(request, 'exams/list_suggestions.html', context)

@login_required
@require_POST
@decorators.ajax_only
@csrf.csrf_exempt
def handle_suggestion(request):
    suggestion_pk = request.POST.get('suggestion_pk')
    action = request.POST.get('action')
    suggestion = get_object_or_404(SuggestedChange.objects.select_related('revision', 'revision__question')\
                                                          .filter(status="PENDING"),
                                   pk=suggestion_pk)

    if action == 'keep' or action == 'submit_edit':
        # Reset approval meta data
        revision_instance = suggestion.revision
        question = revision_instance.question
        revision_instance.approved_by = None
        revision_instance.approval_date = None

        revision_form = forms.RevisionForm(request.POST,
                                           request.FILES,
                                           instance=revision_instance)
        revisionchoiceformset = forms.RevisionChoiceFormset(request.POST,
                                                            instance=revision_instance)

        if revision_form.is_valid() and \
           revisionchoiceformset.is_valid():
            new_revision = revision_form.clone(revision_instance.question, request.user)
            revisionchoiceformset.clone(new_revision)
            # This test relies on choices, so the choices have to be saved
            # before.
            new_revision.is_approved = utils.test_revision_approval(new_revision)
            new_revision.save()
            question.update_is_approved()
            question.save()

        else:
            raise Exception("Could not save the edit!")
        if action == 'keep':
            suggestion.status = 'KEPT'
        if action == 'submit_edit':
            suggestion.status = 'EDITED'
    elif action == 'decline':
        suggestion.status = 'DECLINED'

    suggestion.reviser = request.user
    suggestion.revision_date = timezone.now()
    suggestion.save()
    return {}

@login_required
@require_POST
@decorators.ajax_only
@csrf.csrf_exempt
def update_session_theme(request):
    session_theme_pk = request.POST.get('session_theme_pk')
    session_theme = get_object_or_404(SessionTheme, pk=session_theme_pk)

    profile = request.user.profile
    profile.session_theme = session_theme
    profile.save()

    return {}

@login_required
@require_safe
def share_session(request, slugs, exam_pk, session_pk, secret_key=None):
    category = Category.objects.get_from_slugs_or_404(slugs)
    session = get_object_or_404(Session.objects.select_related('exam',
                                                               'exam__category')\
                                               .undeleted(),
                                pk=session_pk,
                                secret_key=secret_key)

    # PERMISSION CHECK
    if not category.can_user_access(request.user):
        raise PermissionDenied

    previous_session = Session.objects.filter(submitter=request.user,
                                              parent_session=session)\
                                      .first()

    if previous_session:
        return HttpResponseRedirect(reverse("exams:show_session",
                                            args=(slugs, exam_pk, previous_session.pk)))

    context = {'session': session, 'category_slugs': slugs}
    return render(request, "exams/share_session.html", context)

@login_required
@require_safe
@decorators.ajax_only
def get_shared_session_stats(request):
    session_pk = request.GET.get('session_pk')
    session = get_object_or_404(Session, pk=session_pk,
                                is_deleted=False)

    # PERMISSION CHECK
    if not session.can_user_access(request.user):
        raise PermissionDenied

    stats = []
    for shared_session in Session.objects.get_shared(session).exclude(pk=session_pk):
        stat = {'pk': shared_session.pk,
                'has_finished': shared_session.has_finished or False}

        # Only detail the breakdown if the session mode is EXPLAINED.
        # Otherwise, only show a generic count.
        if session.session_mode == 'EXPLAINED':
            stat.update({'correct_count': shared_session.get_correct_count(),
                         'incorrect_count': shared_session.get_incorrect_count(),
                         'skipped_count': shared_session.get_skipped_count()})
        else:
            stat['count'] = shared_session.get_used_questions_count()
        stats.append(stat)

    return {'stats': stats}

