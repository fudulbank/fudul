from dal import autocomplete
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template
from django.views.decorators import csrf
from django.views.decorators.http import require_POST, require_safe
from htmlmin.decorators import minified_response
import json

from core import decorators
from .models import *
from . import forms, utils
import teams.utils
from django.views.decorators.http import require_http_methods
import core.utils
# from reversion.helpers import genericpath

@require_safe
@login_required
def list_meta_categories(request, indicators=False):
    if indicators and not teams.utils.is_editor(request.user):
        raise PermissionDenied

    if indicators:
        show_category_url = 'exams:show_category_indicators'
    else:
        show_category_url = 'exams:show_category'

    subcategories = Category.objects.meta().user_accessible(request.user)
    context = {'subcategories': subcategories,
               'show_category_url': show_category_url,
               'is_indicators_active': indicators,
               'is_browse_active': not indicators,
    }
    return render(request, 'exams/show_category.html', context)

@require_safe
@login_required
def show_category(request, slugs, indicators=False):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    context = {'category': category,
               'is_indicators_active': indicators}

    # PERMISSION CHECK
    if not category.can_user_access(request.user) or\
       indicators and not teams.utils.is_editor(request.user):
        raise PermissionDenied
    subcategories = category.children.user_accessible(request.user)

    if indicators:
        show_category_url = 'exams:show_category_indicators'
        if subcategories.count() == 0:
            return show_category_indicators(request, category)
    else:
        show_category_url = 'exams:show_category'
        # To make sidebar 'active'
        context['is_browse_active'] = True

        # If user can edit, show them all the exams.  Otherwise, only
        # show them exams with approved questions.
        if category.is_user_editor(request.user):
            exams = category.exams.all()
        else:
            exams = category.exams.with_approved_questions()

        context['exams'] = exams

    # If this category has one child, just go to it!
    if subcategories.count() == 1:
        subcategory = subcategories.first()
        return HttpResponseRedirect(reverse(show_category_url,
                                            args=(subcategory.get_slugs(),)))

    context.update({
        'show_category_url': show_category_url,
        'subcategories': subcategories.order_by('name'),
    })

    return render(request, "exams/show_category.html", context)

@require_safe
@login_required
def add_question(request, slugs, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    # PERMISSION CHECK
    exam = get_object_or_404(Exam, pk=pk, category=category)
    # if not exam.can_user_edit(request.user):
    #     raise PermissionDenied
    editor = exam.can_user_edit(request.user)
    instance = Question(exam=exam)
    context = {'exam': exam,
               'question_form': forms.QuestionForm(instance=instance),
               'revision_form': forms.RevisionForm(),
               'explanation_form': forms.ExplanationForm(is_optional=True),
               'revisionchoiceformset': forms.RevisionChoiceFormset(),
               'editor':editor,
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


@csrf.csrf_exempt
@require_POST
@decorators.ajax_only
@login_required
def delete_question(request, pk):
    question_pool = Question.objects.undeleted()\
                                    .select_related('exam',
                                                    'exam__category')
    question = get_object_or_404(question_pool, pk=pk)
    exam = question.exam

    # PERMISSION CHECK
    if not request.user.is_superuser and \
       not exam.category.is_user_editor(request.user) and \
       not question.is_user_creator(request.user):
        raise Exception("You cannot delete that question!")

    question.is_deleted = True
    question.save()

    return {}

@require_POST
@decorators.ajax_only
@login_required
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

        explanation.question = question
        explanation = explanation_form.save()

        template = get_template('exams/partials/exam_stats.html')
        context = {'exam': exam}
        stat_html = template.render(context)
        show_url = reverse('exams:approve_user_contributions', args=(exam.category.get_slugs(), exam.pk))
        full_url = request.build_absolute_uri(show_url)
        return {"message": "success",
                "question_pk": question.pk,
                "stat_html": stat_html,
                "show_url": full_url
                }

    context = {'exam': exam,
               'question_form': question_form,
               'revision_form': revision_form,
               'explanation_form': explanation_form,
               'revisionchoiceformset': revisionchoiceformset}

    return render(request, "exams/partials/question_form.html", context)

@require_safe
@login_required
def list_questions(request, slugs, pk, selector=None):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    exam = get_object_or_404(Exam, pk=pk, category=category)

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context = {'exam': exam,
               'is_browse_active': True}

    if selector:
        question_pool = exam.question_set.all()
        try:
            issue_pk = int(selector)
        except ValueError:
            if selector == 'all':
                questions = question_pool
                context['list_name'] = "all questions"
            elif selector == 'no_answer':
                questions = question_pool.unsolved()
                context['list_name'] = "no right answers"
            elif selector == 'no_issues':
                questions = question_pool.with_no_issues()
                context['list_name'] = "no issues"
            elif selector == 'blocking_issues':
                questions = question_pool.with_blocking_issues()
                context['list_name'] = "blocking issues"
            elif selector == 'nonblocking_issues':
                questions = question_pool.with_nonblocking_issues()
                context['list_name'] = "non-blocking issues"
            elif selector == 'approved':
                questions = question_pool.with_approved_latest_revision()
                context['list_name'] = "approved latesting revision"
            elif selector == 'pending':
                questions = question_pool.with_pending_latest_revision()
                context['list_name'] = "pending latesting revision"
            elif selector == 'lacking_choices':
                questions = question_pool.lacking_choices()
                context['list_name'] = "lacking choices"
            else:
                raise Http404
        else:
            issue = get_object_or_404(Issue, pk=issue_pk)
            context['list_name'] = issue.name
            questions = exam.question_set.undeleted()\
                                         .filter(issues=issue)

        context['questions'] = questions
        return render(request, 'exams/list_questions_by_selector.html', context)
    else:
        context['issues'] = Issue.objects.all()
        return render(request, 'exams/list_questions_index.html', context)

@decorators.ajax_only
@require_safe
@login_required
def show_question(request, pk, revision_pk=None):
    
    question = get_object_or_404(Question, pk=pk, is_deleted=False)
    if revision_pk:
        revision = get_object_or_404(Revision, pk=revision_pk)
        explanation_revision = None
    else:
        revision = question.get_best_latest_revision()
        explanation_revision = question.get_latest_explanation_revision()

    exam = question.exam

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context = {'revision': revision,
               'explanation_revision': explanation_revision}
    return render(request, 'exams/partials/show_question.html', context)

@decorators.ajax_only
@require_safe
@login_required
def show_explanation_revision(request, pk):
    explanation_pool = ExplanationRevision.objects.undeleted()\
                                                  .select_related('question',
                                                                  'question__exam',
                                                                  'question__exam__category')
    explanation_revision = get_object_or_404(explanation_pool, pk=pk)
    exam = explanation_revision.question.exam

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context = {'explanation_revision': explanation_revision}
    return render(request, 'exams/partials/show_explanation.html', context)

@require_safe
@login_required
def list_revisions(request, slugs, exam_pk, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404
    exam = get_object_or_404(Exam, pk=exam_pk, category=category)

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    question = get_object_or_404(Question, pk=pk,
                                 is_deleted=False)
    context = {'question': question,
               'is_browse_active': True,
               'exam': exam}
    return render(request, 'exams/list_revisions.html', context)

@login_required
def submit_revision(request, slugs, exam_pk, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    exam = get_object_or_404(Exam, pk=exam_pk, category=category)
    question = get_object_or_404(Question, pk=pk, is_deleted=False)
    #TODO :latest approved revision
    latest_revision = question.get_latest_revision()
    latest_explanation_revision = question.get_latest_explanation_revision()

    # PERMISSION CHECK
    # if not exam.can_user_edit(request.user):
    #     raise PermissionDenied
    editor = exam.can_user_edit(request.user)
    context = {'editor':editor, 'exam': exam, 'revision': latest_revision}

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
            if new_revision:
                new_revision.is_approved = utils.test_revision_approval(new_revision)
                new_revision.save()

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
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404
    exam = get_object_or_404(Exam, pk=exam_pk, category=category)

    # PERMISSION CHECK
    if not category.can_user_access(request.user):
        raise PermissionDenied

    # If the exam has no approved questions, it doesn't exist for
    # users.
    if not exam.can_user_edit(request.user) and \
       not exam.question_set.undeleted().exists():
        raise Http404

    latest_sessions = exam.session_set.undeleted()\
                                      .with_accessible_questions()\
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

@minified_response
@decorators.ajax_only
@require_safe
@login_required
def list_session_questions(request):
    question_pk = request.GET.get('question_pk')
    session_pk = request.GET.get('session_pk')
    session = get_object_or_404(Session.objects.undeleted(),
                                pk=session_pk)

    current_question = session.get_current_question(question_pk)

    return render(request, "exams/partials/session_question_list.html",
                  {'session': session,
                   'current_question': current_question})

@login_required
@require_safe
def show_session(request, slugs, exam_pk, session_pk, question_pk=None):
    category = Category.objects.get_from_slugs(slugs)
    session = get_object_or_404(Session.objects.select_related('exam',
                                                               'exam__category')\
                                               .undeleted()\
                                               .with_accessible_questions(),
                                pk=session_pk)

    if not category:
        raise Http404

    # PERMISSION CHECK
    if not session.can_user_access(request.user):
        raise PermissionDenied

    current_question = session.get_current_question(question_pk)
    current_question_sequence = session.get_question_sequence(current_question)

    context = {'session': session,
               'current_question': current_question,
               'current_question_sequence': current_question_sequence}

    if question_pk:
        context['current_question_pk'] = question_pk

    return render(request, "exams/show_session.html", context)

@login_required
@require_safe
def show_session_results(request, slugs, exam_pk, session_pk):
    category = Category.objects.get_from_slugs(slugs)

    if not category:
        raise Http404

    session = get_object_or_404(Session.objects.undeleted()\
                                               .select_related('exam')\
                                               .exclude(session_mode__in=['INCOMPLETE', 'SOLVED']),
                                pk=session_pk)

    # PERMISSION CHECK
    if not session.can_user_access(request.user):
        raise PermissionDenied

    if not session.has_finished() and \
       request.user == session.submitter:
        answers = []
        for question in session.get_unused_questions():
            answer = Answer(session=session, question=question)
            answers.append(answer)
        Answer.objects.bulk_create(answers)

    question_pool = session.get_questions()

    correct_questions = question_pool.correct_by_user(request.user)\
                                     .count()
    incorrect_questions = question_pool.incorrect_by_user(request.user)\
                                       .count()
    skipped_questions = question_pool.skipped_by_user(request.user)\
                                     .count()


    context = {'session': session, 'exam': session.exam,
               'correct_questions': correct_questions,
               'incorrect_questions': incorrect_questions,
               'skipped_questions': skipped_questions
    }

    return render(request, 'exams/show_session_results.html', context)

@decorators.ajax_only
@require_POST
@login_required
@csrf.csrf_exempt
def toggle_marked(request):
    question_pk = request.POST.get('question_pk')
    session_pk = request.POST.get('session_pk')
    session = get_object_or_404(Session.objects.undeleted(),
                                pk=session_pk)
    question = get_object_or_404(session.get_questions(), pk=question_pk,
                                 is_deleted=False)

    # PERMISSION CHECKS
    if not session.can_user_access(request.user):
        raise Exception("You cannot mark questions in this session.")

    if utils.is_question_marked(question, request.user):
        question.marking_users.remove(request.user)
        is_marked = False
    else:
        question.marking_users.add(request.user)
        is_marked = True

    return {'is_marked': is_marked}

@decorators.ajax_only
@require_POST
@login_required
@csrf.csrf_exempt
def submit_highlight(request):
    # PERMISSION CHECKS
    session_pk = request.POST.get('session_pk')
    session = get_object_or_404(Session.objects.undeleted(),
                                pk=session_pk)
    if not session.can_user_access(request.user):
        raise PermissionDenied

    best_latest_revision_pk = request.POST.get('best_latest_revision_pk')
    best_latest_revision = get_object_or_404(Revision,
                                             pk=best_latest_revision_pk)
    stricken_choice_pks = request.POST.get('stricken_choice_pks', '[]')
    stricken_choice_pks = json.loads(stricken_choice_pks)
    stricken_choices = Choice.objects.filter(pk__in=stricken_choice_pks)
    highlighted_text = request.POST.get('highlighted_text', '')
 
    try:
        highlight = Highlight.objects.get(session=session,
                                          revision=best_latest_revision)
    except Highlight.DoesNotExist:
        highlight = Highlight.objects.create(session=session,
                                             revision=best_latest_revision)

    highlight.revision = best_latest_revision

    if not '<span ' in highlighted_text:
        highlighted_text = ""

    # Save a database hit if the highlighted text ha not changed
    if highlight.highlighted_text != highlighted_text:
        highlight.highlighted_text = highlighted_text
        highlight.save()

    highlight.stricken_choices = stricken_choices

    return {}

@decorators.ajax_only
@require_POST
@login_required
@csrf.csrf_exempt
def submit_answer(request):
    question_pk = request.POST.get('question_pk')
    session_pk = request.POST.get('session_pk')
    choice_pk = request.POST.get('choice_pk')
    session = get_object_or_404(Session.objects.undeleted(), pk=session_pk)
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

    return {}

@require_safe
@login_required
def list_previous_sessions(request):
    sessions = request.user.session_set\
                           .select_related('exam', 'exam__category')\
                           .undeleted()\
                           .with_accessible_questions()

    context = {'sessions':sessions,
               'is_previous_active': True}

    return render(request, 'exams/list_previous_sessions.html',
                  context)

@require_safe
@login_required
def show_category_indicators(request, category):
    # PERMISSION CHECK
    if not teams.utils.is_editor(request.user):
        raise PermissionDenied

    context = {'category': category,
               'is_indicators_active': True}
    return render(request, 'exams/show_category_indicators.html', context)

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
        revision_form = forms.RevisionForm(instance=latest_revision)
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
            return {}

    context = {'question': question,
               'revision_form': revision_form,
               'revisionchoiceformset': revisionchoiceformset}

    return render(request, 'exams/partials/contribute_revision.html', context)

@login_required
def approve_user_contributions(request,slugs,exam_pk):

    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

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
def show_revision_comparison(request, pk, revision_pk=None):
    question_pool = Question.objects.undeleted()\
                                    .select_related('exam')
    question = get_object_or_404(question_pool, pk=pk)

    if revision_pk:
        revision = get_object_or_404(Revision, pk=revision_pk,
                                     is_deleted=False)
    else:
        revision = question.get_latest_revision()

    exam = question.exam

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context = {'revision': revision,'exam':exam}
    return render(request, 'exams/partials/show_revision_comparison.html', context)

@csrf.csrf_exempt
@require_POST
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
       not exam.category.is_user_editor(request.user) and \
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

    return {}


@csrf.csrf_exempt
@require_POST
@decorators.ajax_only
def delete_explanation_revision(request, pk):
    explanation_pool = ExplanationRevision.objects.undeleted()\
                                                  .select_related('question',
                                                                  'question__exam',
                                                                  'question__exam__category')
    explanation_revision = get_object_or_404(explanation_pool, pk=pk)
    question = explanation_revision.question
    exam = question.exam

    # PERMISSION CHECK
    if not request.user.is_superuser and \
       not exam.category.is_user_editor(request.user) and \
       not explanation_revision.submitter == request.user:
        raise Exception("You cannot delete this explanation!")

    explanation_revision.is_deleted = True
    explanation_revision.save()

    # Mark the new last explanation as such
    question.update_latest()

    return {}

@csrf.csrf_exempt
@require_POST
@decorators.ajax_only
def mark_revision_approved(request, pk):
    revision_pool = Revision.objects.undeleted()\
                                    .select_related('question',
                                                    'question__exam')
    revision = get_object_or_404(revision_pool, pk=pk)
    exam = revision.question.exam

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise Exception("You cannot change the approval status.")

    revision.is_approved = True
    revision.approved_by= request.user
    revision.save()

@require_POST
@decorators.ajax_only
@csrf.csrf_exempt
def mark_revision_pending(request, pk):
    revision_pool = Revision.objects.undeleted()\
                                    .select_related('question',
                                                    'question__exam')
    revision = get_object_or_404(revision_pool, pk=pk)
    exam = revision.question.exam

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise Exception("You cannot change the approval status.")

    revision.is_approved = False
    revision.approved_by= request.user
    revision.save()


@login_required
def approve_question(request, slugs, exam_pk, pk):
    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

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
               'editor': editor,
               'question': question}

    return render(request, "exams/add_question.html", context)

@require_safe
@login_required
def show_my_performance(request):
    total_questions = Question.objects.approved()\
                                      .used_by_user(request.user,
                                                    exclude_skipped=False)\
                                      .count()
    correct_questions = Question.objects.approved()\
                                        .correct_by_user(request.user)\
                                        .count()
    incorrect_questions = Question.objects.approved()\
                                          .incorrect_by_user(request.user)\
                                          .count()
    skipped_questions = Question.objects.approved()\
                                        .skipped_by_user(request.user)\
                                        .count()

    # Only get exams which the user has taken
    exams = Exam.objects.filter(session__submitter=request.user,
                                session__is_deleted=False,
                                session__answer__isnull=False).distinct()

    context = {'correct_questions': correct_questions,
               'incorrect_questions': incorrect_questions,
               'skipped_questions': skipped_questions,
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
    correct_questions =  utils.get_user_question_stats(target=exam,
                                                       user=request.user,
                                                       result='correct')
    incorrect_questions =  utils.get_user_question_stats(target=exam,
                                                         user=request.user,
                                                         result='incorrect')
    skipped_questions =  utils.get_user_question_stats(target=exam,
                                                       user=request.user,
                                                       result='skipped')
    context = {'correct_questions': correct_questions,
               'incorrect_questions': incorrect_questions,
               'skipped_questions': skipped_questions,
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
    if user_pk:
        user = get_object_or_404(User,pk=user_pk)
    else:
        user = request.user

    revisions = Revision.objects.filter(submitter=user)
    exams = Exam.objects.all()

    return render(request, 'exams/list_contributions.html',{'revisions':revisions,'exams':exams})

@require_safe
@login_required
@require_http_methods(['GET'])
def search(request):
    q = request.GET.get('q')
    categories= utils.get_user_allowed_categories(request.user)
    #TODO:try to add choices to search
    if q:
        search_fields =['pk','revision__text','revision__choice__text']
        if teams.utils.is_editor(request.user):
            qs = Question.objects.filter(subjects__exam__category__in=categories,revision__is_last=True,revision__is_deleted=False).distinct()
        else:
            qs = Question.objects.filter(subjects__exam__category__in=categories,revision__is_last=True, revision__is_approved=True,revision__is_deleted=False).distinct()
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
        if AnswerCorrection.objects.filter(choice=choice).exists():
            correction = AnswerCorrection.objects.get(choice=choice)
            if correction.submitter == request.user:
                raise Exception("You were the one that submitted this correction, so you cannot vote.")

            if action in ['add', 'support']:
                if correction.supporting_users.filter(pk=request.user.pk).exists():
                    raise Exception("You have already supported this correction.")
                elif correction.opposing_users.filter(pk=request.user.pk).exists():
                    correction.opposing_users.remove(request.user)
                correction.supporting_users.add(request.user)
                # TODO: Notify the submitter that people are supporting
                # their contribution
            elif action == 'oppose':
                if correction.opposing_users.filter(pk=request.user.pk).exists():
                    raise Exception("You have already opposed this correction.")
                elif correction.supporting_users.filter(pk=request.user.pk).exists():
                    correction.supporting_users.remove(request.user)
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


@csrf.csrf_exempt
@require_POST
@decorators.ajax_only
@login_required
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

@csrf.csrf_exempt
@require_POST
@decorators.ajax_only
@login_required
def delete_session(request):
    if not 'deletion_type' in request.POST:
        return HttpResponseBadRequest()
    deletion_type = request.POST['deletion_type']

    if deletion_type == 'all':
        request.user.session_set.update(is_deleted=True)
    elif deletion_type == 'exam':
        exam_pk = request.POST.get('pk')
        exam = Exam.objects.get(pk=exam_pk)
        request.user.session_set.filter(exam=exam).update(is_deleted=True)
    elif deletion_type == 'session':
        session_pk = request.POST.get('pk')
        session = Session.objects.get(pk=session_pk)
        # PERMISSION CHECK
        if session.submitter == request.user:
            session.is_deleted = True
            session.save()
        else:
            raise Exception("You cannot ask for forgiveness for this session.")

    return {}

@csrf.csrf_exempt
@require_safe
@decorators.ajax_only
def count_answers(request):
    return {'answer_count': Answer.objects\
                                  .filter(choice__isnull=False)\
                                  .count()
            }
