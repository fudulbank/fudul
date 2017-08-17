from dal import autocomplete
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseBadRequest
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
    # if not exam.can_user_edit(request.user):
    #     raise PermissionDenied
    editor = exam.can_user_edit(request.user)
    context = {'exam': exam,
               'questionform': forms.QuestionForm(exam=exam),
               'revisionform': forms.RevisionForm(),
               'revisionchoiceformset': forms.RevisionChoiceFormset(),
               'editor':editor}

    return render(request, "exams/add_question.html", context)


class QuestionAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        exam_pk = self.forwarded.get('exam_pk')
        exam = Exam.objects.get(pk=exam_pk)
        qs = exam.get_questions().order_by_submission().filter(parent_question__isnull=True)\
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
def handle_question(request, exam_pk,question_pk=None):
    exam = get_object_or_404(Exam, pk=exam_pk)

    # # PERMISSION CHECK
    # if not exam.can_user_edit(request.user):
    #     raise PermissionDenied
    if question_pk :
        question = get_object_or_404(Question, pk=question_pk)
        instance = question.get_latest_revision()
        questionform = forms.QuestionForm(request.POST,
                                          exam=exam,
                                          instance=question)
        revisionform = forms.RevisionForm(request.POST,
                                          request.FILES,
                                          instance=instance)
    else:
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
    #TODO :latest approved revision
    latest_revision = question.get_latest_revision()

    # PERMISSION CHECK
    # if not exam.can_user_edit(request.user):
    #     raise PermissionDenied
    editor = exam.can_user_edit(request.user)
    context = {'editor':editor,'exam': exam, 'revision': latest_revision}

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


@login_required
def create_session(request, slugs, exam_pk):

    category = Category.objects.get_from_slugs(slugs)
    if not category:
        raise Http404

    exam = get_object_or_404(Exam, pk=exam_pk, category=category)


    question_count = exam.get_approved_questions().count()
    editor = teams.utils.is_editor(request.user)
    context = {'exam': exam,
               'question_count': question_count,
               'editor':editor}

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

@login_required
def show_session(request, slugs, exam_pk, session_pk, question_pk=None):
    category = Category.objects.get_from_slugs(slugs)
    session = get_object_or_404(Session, pk=session_pk)

    if not category:
        raise Http404

    # PERMISSION CHECK
    if not session.can_access(request.user):
        raise PermissionDenied

    # If a question PK is given, show it.  Otheriwse show the first
    # session unused question.  Otherwise, show the first session
    # question.
    if question_pk:
        current_question = get_object_or_404(session.questions, pk=question_pk)
    elif not session.has_finished():
        current_question = session.get_unused_questions().first()
    else:
        current_question = session.questions.order_by('global_sequence').first()

    current_question_sequence = session.get_question_sequence(current_question)

    return render(request, "exams/show_session.html", {'session': session,
                                                       'current_question': current_question,
                                                       'current_question_sequence': current_question_sequence})

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
    question = get_object_or_404(session.questions, pk=question_pk)

    # PERMISSION CHECKS
    if not session.can_access(request.user):
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
def navigate_question(request):
    question_pk = request.POST.get('question_pk')
    session_pk = request.POST.get('session_pk')
    action = request.POST.get('action')
    session = get_object_or_404(Session, pk=session_pk)
    current_question = get_object_or_404(session.questions, pk=question_pk)

    # PERMISSION CHECK
    if not session.can_access(request.user):
        raise Exception("You cannot mark questions in this sessions")

    question_pool = session.questions.order_by('global_sequence')
    global_sequence = current_question.global_sequence
    if action == 'next':
        question = question_pool.exclude(global_sequence__lte=global_sequence).first()
    elif action == 'previous':
        question = question_pool.exclude(global_sequence__gte=global_sequence).last()
    else:
        return HttpResponseBadRequest("No valid action was provided.")

    if not question:
        raise Exception("No %s question" % action)        

    question_sequence = session.get_question_sequence(question)
    template = get_template('exams/partials/session_question.html')
    context = {'question': question, 'session': session}
    question_body = template.render(context)
    is_marked = utils.is_question_marked(question, request.user)
    url = question.get_session_url(session)

    return {"is_marked": is_marked,
            'url': url,
            'question_sequence': question_sequence,
            'question_pk': question.pk,
            "question_body": question_body}

@decorators.ajax_only
@decorators.post_only
@login_required
@csrf.csrf_exempt
def submit_answer(request):
    question_pk = request.POST.get('question_pk')
    session_pk = request.POST.get('session_pk')
    choice_pk = request.POST.get('choice_pk')
    session = get_object_or_404(Session, pk=session_pk)
    question = get_object_or_404(session.questions, pk=question_pk)

    # PERMISSION CHECKS
    if not session.can_access(request.user):
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

    next_question = session.questions.order_by('global_sequence')\
                                     .exclude(pk__lte=question.pk)\
                                     .exists()
    if next_question:
        done = False
    else:
        done = True

    return {'done': done,
            'right_choice_pk': right_choice_pk,
            'explanation': explanation}

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

class ExamTypeQuestionCount(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        exam_pk = self.forwarded.get('exam_pk')
        exam = Exam.objects.get(pk=exam_pk)
        qs = exam.get_exam_types()
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

@login_required
@decorators.ajax_only
@csrf.csrf_exempt
def contribute_explanation(request):
    question_pk = request.GET.get('question_pk')
    question = get_object_or_404(Question, pk=question_pk)
    latest_revision = question.get_latest_revision()

    if request.method == 'GET':
        form = forms.ExplanationForm(instance=latest_revision)
    elif request.method == 'POST':
        form = forms.ExplanationForm(request.POST,
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
        revisionchoiceformset = forms.RevisionChoiceFormset(instance=latest_revision)
    elif request.method == 'POST':
        revisionform = forms.RevisionForm(request.POST,
                                          request.FILES,
                                          instance=latest_revision)

        revisionchoiceformset = forms.RevisionChoiceFormset(request.POST,
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
    revisions = Revision.objects.per_exam(exam).filter(is_contribution =True,is_deleted=False).exclude(question__pk__in=pks)
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
        revision = get_object_or_404(Revision, pk=revision_pk)
    else:
        revision = question.get_latest_revision()

    exam = question.get_exam()

    # PERMISSION CHECK
    if not exam.can_user_edit(request.user):
        raise PermissionDenied

    context = {'revision': revision,'exam':exam}
    return render(request, 'exams/partials/show_revision_comparison.html', context)

@csrf.csrf_exempt
@decorators.post_only
@decorators.ajax_only
def remove_revision(request, pk):
    revision = get_object_or_404(Revision, pk=pk)
    exam = revision.question.subjects.first.exam

    # PERMISSION CHECK
    if not request.user.is_superuser and \
            not exam.category.is_user_editor(request.user) and \
            not revision.submitter == request.user:
        raise Exception("You cannot delete that question!")

    revision.is_deleted = True
    revision.save()

    return {}

@csrf.csrf_exempt
@decorators.post_only
@decorators.ajax_only
def approve_revision (request, pk):
    revision = get_object_or_404(Revision, pk=pk)
    exam = revision.question.subjects.first.exam

    # PERMISSION CHECK
    if not request.user.is_superuser and \
            not exam.category.is_user_editor(request.user) and \
            not revision.submitter == request.user:
        raise Exception("You cannot delete that question!")

    revision.is_approved = True
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
               'questionform': forms.QuestionForm(exam=exam,instance=question),
               'revisionform': forms.RevisionForm(instance=revision),
               'revisionchoiceformset': forms.RevisionChoiceFormset(instance=revision),
               'editor':editor,
               'question':question}

    return render(request, "exams/add_question.html", context)

