from dal import autocomplete
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template
from django.views.decorators import csrf
from htmlmin.decorators import minified_response

from core import decorators
from .models import Exam, Question, Category, Revision, Session, Choice, Answer, Status
from . import forms, utils
import teams.utils
from django.views.decorators.http import require_http_methods
from django.db.models import Q

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


@decorators.get_only
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
               'questionform': forms.QuestionForm(instance=instance),
               'revisionform': forms.RevisionForm(),
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
    exam = question.exam

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
def handle_question(request, exam_pk,question_pk=None):
    exam = get_object_or_404(Exam, pk=exam_pk)

    # # PERMISSION CHECK
    # if not exam.can_user_edit(request.user):
    #     raise PermissionDenied
    if question_pk :
        question = get_object_or_404(Question, pk=question_pk,
                                     is_deleted=False)
        instance = question.get_latest_revision()
        questionform = forms.QuestionForm(request.POST,
                                          instance=question)
        revisionform = forms.RevisionForm(request.POST,
                                          request.FILES,
                                          instance=instance)
        revisionchoiceformset = forms.RevisionChoiceFormset(request.POST,
                                                            instance=instance,)
    else:
        question_instance = Question(exam=exam)
        questionform = forms.QuestionForm(request.POST,
                                          instance=question_instance)
        revision_instance = Revision(submitter=request.user, is_first=True,
                            is_last=True)
        revisionform = forms.RevisionForm(request.POST,
                                          request.FILES,
                                          instance=revision_instance)
        revisionchoiceformset = forms.RevisionChoiceFormset(request.POST)

    if questionform.is_valid() and revisionform.is_valid() and revisionchoiceformset.is_valid():
        question = questionform.save()
        revision = revisionform.save(commit=False)
        revision.question = question
        revision.save()
        revisionform.save_m2m()

        revision.is_approved = utils.test_revision_approval(revision)

        revision.save()

        if teams.utils.is_editor(request.user):
            revision.is_contribution = False
        else:
            revision.is_contribution = True

        revision.save()
        revisionchoiceformset.instance = revision

        revisionchoiceformset.save()

        template = get_template('exams/partials/exam_stats.html')
        context = {'exam': exam}
        stat_html = template.render(context)
        show_url = reverse('exams:approve_user_contributions', args=(exam.category.get_slugs(),exam.pk))
        full_url = request.build_absolute_uri(show_url)
        return {"message": "success",
                "question_pk": question.pk,
                "stat_html": stat_html,
                "show_url": full_url
                }

    context = {'exam': exam,
               'questionform': questionform,
               'revisionform': revisionform,
               'revisionchoiceformset': revisionchoiceformset}

    return render(request, "exams/partials/question_form.html", context)


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
        try:
            status_pk = int(selector)
        except ValueError:
            if selector == 'no_answer':
                questions = exam.question_set.unsolved()
                context['list_name'] = "no right answers"
            elif selector == 'approved':
                latest_revision_pks = exam.get_approved_latest_revisions()\
                                          .values_list('question__pk', flat=True)
                questions = Question.objects.filter(pk__in=latest_revision_pks)
                context['list_name'] = "approved latesting revision"                
            elif selector == 'pending':
                latest_revision_pks = exam.get_pending_latest_revisions()\
                                          .values_list('question__pk', flat=True)
                questions = Question.objects.filter(pk__in=latest_revision_pks)
                context['list_name'] = "pending latesting revision"
        else:
            status = get_object_or_404(Status, pk=status_pk)
            context['list_name'] = status.name
            questions = exam.question_set.undeleted()\
                                         .filter(statuses=status)

        context['questions'] = questions
        return render(request, 'exams/list_questions_by_selector.html', context)
    else:
        context['statuses'] = Status.objects.all()
        return render(request, 'exams/list_questions_index.html', context)

@login_required
@decorators.ajax_only
def show_question(request, pk, revision_pk=None):
    question = get_object_or_404(Question, pk=pk, is_deleted=False)
    if revision_pk:
        revision = get_object_or_404(Revision, pk=revision_pk)
    else:
        revision = question.get_latest_revision()

    exam = question.exam

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

    exam = get_object_or_404(Exam, pk=exam_pk)
    question = get_object_or_404(Question, pk=pk, is_deleted=False)
    #TODO :latest approved revision
    latest_revision = question.get_latest_revision()

    # PERMISSION CHECK
    # if not exam.can_user_edit(request.user):
    #     raise PermissionDenied
    editor = exam.can_user_edit(request.user)
    context = {'editor':editor,'exam': exam, 'revision': latest_revision}

    if request.method == 'POST':
        questionform = forms.QuestionForm(request.POST,
                                          instance=question)
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
        questionform = forms.QuestionForm(instance=question)
        revisionform = forms.RevisionForm(instance=latest_revision)
        revisionchoiceformset = forms.RevisionChoiceFormset(instance=latest_revision)
    context['questionform'] = questionform
    context['revisionform'] = revisionform
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
       not exam.question_set.approved().exists():
        raise Http404
 
    latest_sessions = exam.session_set.with_approved_questions()\
                                      .filter(submitter=request.user)\
                                      .order_by('-pk')[:5]

    question_count = exam.question_set.approved().count()
    editor = teams.utils.is_editor(request.user)
    context = {'exam': exam,
               'question_count': question_count,
               'editor':editor,
               'latest_sessions': latest_sessions,
               'is_browse_active': True, # To make sidebar 'active'
    }

    if request.method == 'GET':
        sessionform = forms.SessionForm(exam=exam)
    elif request.method == 'POST':
        instance = Session(submitter=request.user, exam=exam)
        sessionform = forms.SessionForm(request.POST,
                                        instance=instance, exam=exam)
        if sessionform.is_valid():
            # Question allocation happens in SessionForm.save()
            session = sessionform.save()
            return HttpResponseRedirect(reverse("exams:show_session",
                                                args=(session.exam.category.get_slugs(),session.exam.pk,session.pk)))
    context['sessionform'] = sessionform

    return render(request, "exams/create_session.html", context)

@minified_response
@decorators.ajax_only
@decorators.get_only
@login_required
def list_session_questions(request):
    question_pk = request.GET.get('question_pk')
    session_pk = request.GET.get('session_pk')
    session = get_object_or_404(Session, pk=session_pk)

    current_question = session.get_current_question(question_pk)

    return render(request, "exams/partials/session_question_list.html",
                  {'session': session,
                   'current_question': current_question})

@login_required
def show_session(request, slugs, exam_pk, session_pk, question_pk=None):
    category = Category.objects.get_from_slugs(slugs)
    session = get_object_or_404(Session.objects.with_approved_questions(), pk=session_pk)

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
def show_session_results(request, slugs, exam_pk, session_pk):
    category = Category.objects.get_from_slugs(slugs)
    session = get_object_or_404(Session, pk=session_pk)
    exam = session.exam
    if not category:
        raise Http404

    if not session.has_finished():
        answers = []
        for question in session.get_unused_questions():
            answer = Answer(session=session, question=question)
            answers.append(answer)
        Answer.objects.bulk_create(answers)

    context = {'session': session,'exam':exam}

    return render(request, 'exams/show_session_results.html', context)

@decorators.ajax_only
@decorators.post_only
@login_required
@csrf.csrf_exempt
def toggle_marked(request):
    question_pk = request.POST.get('question_pk')
    session_pk = request.POST.get('session_pk')
    session = get_object_or_404(Session, pk=session_pk)
    question = get_object_or_404(session.questions.approved(), pk=question_pk,
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
@decorators.post_only
@login_required
@csrf.csrf_exempt
def submit_answer(request):
    question_pk = request.POST.get('question_pk')
    session_pk = request.POST.get('session_pk')
    choice_pk = request.POST.get('choice_pk')
    session = get_object_or_404(Session, pk=session_pk)
    question = get_object_or_404(session.questions.approved(), pk=question_pk, is_deleted=False)

    # PERMISSION CHECKS
    if not session.can_user_access(request.user):
        raise Exception("You cannot submit answers in this session")
    if question.was_solved_in_session(session):
        raise Exception("Question #{} was previously solved in this session.".format(question_pk))

    if choice_pk:
        choice = get_object_or_404(Choice, pk=choice_pk)
    else:
        choice = None

    latest_revision = question.get_latest_approved_revision()

    answer = Answer.objects.create(session=session, question=question,
                                   choice=choice)

    # Only return the explanation if the session mode is explained,
    # and an explanation exists.
    if session.session_mode == 'EXPLAINED' and \
       latest_revision.explanation:
        explanation = latest_revision.explanation
    else:
        explanation = None

    # Only return the right answer if the session mode is explained.
    if session.session_mode == 'EXPLAINED':
        try:
            right_choice = latest_revision.choice_set.get(is_right=True)
        except Choice.DoesNotExist:
            raise Exception("We don't have the right answer for this question.")
        else:
            right_choice_pk = right_choice.pk
    else:
        right_choice_pk = None

    next_question = session.questions.approved()\
                                     .order_by('global_sequence')\
                                     .exclude(pk__lte=question.pk)\
                                     .exists()
    if next_question:
        done = False
    else:
        done = True

    return {'done': done,
            'right_choice_pk': right_choice_pk,
            'explanation': explanation}

@login_required
def list_previous_sessions(request):
    sessions = Session.objects.filter(submitter=request.user)\
                              .with_approved_questions()

    context = {'sesstions':sessions,
               'is_previous_active': True}

    return render(request, 'exams/list_previous_sessions.html',
                  context)

class SubjectQuestionCount(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        exam_pk = self.forwarded.get('exam_pk')
        exam = Exam.objects.get(pk=exam_pk)

        # Make sure we only show subjects that actually have approved
        # questions
        qs = exam.subject_set.with_approved_questions()

        if self.q:
            qs = qs.filter(pk=self.q)
        return qs

    def get_result_label(self, item):
        return "<strong>{}</strong> ({})".format(item.name, item.question_set.approved().count())

class ExamTypeQuestionCount(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        exam_pk = self.forwarded.get('exam_pk')
        exam = Exam.objects.get(pk=exam_pk)

        # Make sure we only show exam types that actually have
        # approved questions
        qs = exam.exam_types.with_approved_questions()

        if self.q:
            qs = qs.filter(pk=self.q)
        return qs

    def get_result_label(self, item):
        return "<strong>{}</strong> ({})".format(item.name, item.question_set.approved().count())


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
    latest_revision = question.get_latest_revision()

    if request.method == 'GET':
        form = forms.ExplanationForm(instance=latest_revision)
    elif request.method == 'POST':
        form = forms.ExplanationForm(request.POST,
                                     request.FILES,
                                     instance=latest_revision)
        if form.is_valid():
            form.clone(question, request.user)
            return {}

    context = {'question': question,
               'form': form}
    return render(request, 'exams/partials/contribute_explanation.html', context)

@login_required
@decorators.ajax_only
@csrf.csrf_exempt
def contribute_revision(request):
    question_pk = request.GET.get('question_pk')
    question = get_object_or_404(Question, pk=question_pk)
    latest_revision = question.get_latest_revision()

    if request.method == 'GET':
        revisionform = forms.RevisionForm(instance=latest_revision)
        revisionchoiceformset = forms.ContributedRevisionChoiceFormset(instance=latest_revision)
    elif request.method == 'POST':
        revisionform = forms.RevisionForm(request.POST,
                                          request.FILES,
                                          instance=latest_revision)

        revisionchoiceformset = forms.ContributedRevisionChoiceFormset(request.POST,
                                                            instance=latest_revision)
        if revisionform.is_valid() and revisionchoiceformset.is_valid():
            new_revision = revisionform.clone(question,request.user)
            revisionchoiceformset.clone(new_revision)
            return {}

    context = {'question': question,
               'revisionform': revisionform,
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

    question = get_object_or_404(Question, pk=pk)

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
@decorators.post_only
@decorators.ajax_only
def delete_revision(request, pk):
    revision = get_object_or_404(Revision, pk=pk)
    question = revision.question
    exam = question.exam

    # PERMISSION CHECK
    if not request.user.is_superuser and \
            not exam.category.is_user_editor(request.user) and \
            not revision.submitter == request.user:
        raise Exception("You cannot delete that question!")

    revision.is_deleted = True
    revision.save()

    # If no undeleted revision remains, then mark the whole question
    # as deleted as well.
    if not question.revision_set.undeleted().count():
        question.is_deleted = True
        question.save()

    return {}

@csrf.csrf_exempt
@decorators.post_only
@decorators.ajax_only
def mark_revision_approved(request, pk):
    revision = get_object_or_404(Revision, pk=pk)
    exam = revision.question.exam

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise Exception("You change the approval status.")

    revision.is_approved = True
    revision.save()

@csrf.csrf_exempt
@decorators.post_only
@decorators.ajax_only
def mark_revision_pending(request, pk):
    revision = get_object_or_404(Revision, pk=pk)
    exam = revision.question.exam

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise Exception("You change the approval status.")

    revision.is_approved = False
    revision.save()


@login_required
def approve_question(request, slugs, exam_pk,pk):
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
               'questionform': forms.QuestionForm(instance=question),
               'revisionform': forms.RevisionForm(instance=revision),
               'revisionchoiceformset': forms.RevisionChoiceFormset(instance=revision),
               'editor':editor,
               'question':question}

    return render(request, "exams/add_question.html", context)

@login_required
def show_my_performance(request):
    answer_pool = Answer.objects.filter(session__submitter=request.user)
    total_answers = answer_pool.count()
    correct_answers = answer_pool.filter(choice__is_right=True).count()
    incorrect_answers = answer_pool.filter(choice__is_right=False).count()
    skipped_answers = answer_pool.filter(choice__isnull=True).count()

    # Only get exams which the user has taken
    exams = Exam.objects.filter(session__submitter=request.user).distinct()

    context = {'correct_answers': correct_answers,
               'incorrect_answers': incorrect_answers,
               'skipped_answers': skipped_answers,
               'exams': exams,
               'is_performance_active': True}

    return render(request, "exams/show_my_performance.html", context)

@login_required
def show_my_performance_per_exam(request, exam_pk):
    user_exams = Exam.objects.filter(session__submitter=request.user).distinct()
    exam = get_object_or_404(user_exams, pk=exam_pk)
    correct_answers =  utils.get_user_answer_stats(target=exam,
                                                   user=request.user,
                                                   result='correct')
    incorrect_answers =  utils.get_user_answer_stats(target=exam,
                                                     user=request.user,
                                                     result='incorrect')
    skipped_answers =  utils.get_user_answer_stats(target=exam,
                                                   user=request.user,
                                                   result='correct')
    context = {'correct_answers': correct_answers,
               'incorrect_answers': incorrect_answers,
               'skipped_answers': skipped_answers,
               'exam': exam,
               'is_performance_active': True}

    return render(request, "exams/show_my_performance_per_exam.html", context)

@login_required
def show_credits(request,pk):
    exam = get_object_or_404(Exam, pk=pk)
    return render(request, 'exams/partials/show_credits.html',{'exam':exam})


@login_required
def list_contributions(request,user_pk=None):
    if user_pk:
        user = get_object_or_404(User,pk=user_pk)
    else:
        user = request.user

    revisions = Revision.objects.filter(submitter=user)
    exams = Exam.objects.all()

    return render(request, 'exams/list_contributions.html',{'revisions':revisions,'exams':exams})


@require_http_methods(['GET'])
def search(request):
    q = request.GET.get('q')
    #TODO:try to add choices to search
    #what about questions that the user isnt allowed to see
    if q:
        revisions = Revision.objects.filter(is_last=True, is_approved=True).filter(Q(question__pk=q)| Q(text__icontains=q))
        return render(request, 'exams/search_results.html', {'revisions': revisions, 'query': q})
    return HttpResponse('Please submit a search term.')
