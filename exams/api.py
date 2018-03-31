from django.http import HttpResponseBadRequest, Http404
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import truncatewords, linebreaksbr
from django.template.loader import get_template
from rest_framework import exceptions, serializers, views, viewsets, permissions, pagination
from rest_framework.response import Response
import textwrap

from exams.models import *
import accounts.utils
import teams.utils

class RulesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = ('regex_pattern', 'regex_replacement', 'scope')

class ChoiceIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ('id', 'is_right')

class AnswerSerializer(serializers.ModelSerializer):
    choice = ChoiceIdSerializer(read_only=True)

    class Meta:
        model = Answer
        fields = ('question_id', 'choice')

class ChoiceTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ('id', 'text', 'is_right')

class RevisionTextSerializer(serializers.ModelSerializer):
    choice_set = ChoiceTextSerializer(read_only=True, many=True)

    class Meta:
        model = Revision
        fields = ('id', 'question_id', 'text', 'choice_set')

class QuestionTextSerializer(serializers.ModelSerializer):
    latest_revision = RevisionTextSerializer(read_only=True,
                                             source='get_latest_revision')

    class Meta:
        model = Question
        fields = ('id', 'latest_revision', 'get_answering_user_count',
                  'get_list_revision_url')

class DuplicateSerializer(serializers.ModelSerializer):
    question = QuestionTextSerializer(read_only=True)

    class Meta:
        model = Duplicate
        fields = ('question', 'ratio', 'get_percentage')

class QuestionIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ('id',)

class SuggestedChangeSerializer(serializers.ModelSerializer):
    revision = RevisionTextSerializer(read_only=True)
    rules = RulesSerializer(read_only=True, many=True)

    class Meta:
        model = SuggestedChange
        fields = ('id', 'revision', 'rules')

class DuplicateContainerSerializer(serializers.ModelSerializer):
    primary_question = QuestionTextSerializer(read_only=True)
    duplicate_set = DuplicateSerializer(read_only=True, many=True)

    class Meta:
        model = DuplicateContainer
        fields = ('id', 'primary_question', 'duplicate_set')

class RevisionSummarySerializer(serializers.ModelSerializer):
    question = QuestionIdSerializer(read_only=True)
    summary = serializers.SerializerMethodField()
    assigned_editor = serializers.SerializerMethodField()

    def get_assigned_editor(self, obj):
        return accounts.utils.get_user_credit(obj.question.assigned_editor)

    def get_summary(self, obj):
        return linebreaksbr(truncatewords(obj.text, 70))

    class Meta:
        model = Revision
        fields = ('question', 'summary', 'submission_date',
                  'assigned_editor')
        
class RevisionAssignmentSerializer(serializers.ModelSerializer):
    question = QuestionIdSerializer(read_only=True)
    summary = serializers.SerializerMethodField()
    category_slugs = serializers.SerializerMethodField()
    exam_id = serializers.SerializerMethodField()

    def get_summary(self, obj):
        return linebreaksbr(truncatewords(obj.text, 70))

    def get_category_slugs(self, obj):
        return obj.question.exam.category.get_slugs()

    def get_exam_id(self, obj):
        return obj.question.exam_id

    class Meta:
        model = Revision
        fields = ('question', 'summary', 'submission_date',
                  'category_slugs', 'exam_id')

class RevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revision
        fields = ('id', 'question_id')

class HighlightSerializer(serializers.ModelSerializer):
    revision = RevisionSerializer(read_only=True)

    class Meta:
        model = Highlight
        fields = ('revision', 'highlighted_text', 'stricken_choices')

def has_access_question(question_pk, user):
    pool = Question.objects.select_related('exam').undeleted()
    question = get_object_or_404(pool, pk=question_pk)
    return question.exam.can_user_access(user)

class HasSessionAccess(permissions.BasePermission):
    def has_permission(self, request, view):
        session_pk = request.query_params.get('session_pk')
        if not session_pk:
            return False

        session = get_object_or_404(Session.objects.select_related('submitter'), pk=session_pk)
        return session.can_user_access(request.user)

class HasSessionOrQuestionAccess(permissions.BasePermission):
    def has_permission(self, request, view):
        session_pk = request.query_params.get('session_pk')
        question_pk = request.query_params.get('question_pk')

        if question_pk:
            return has_access_question(question_pk, request.user)
        elif session_pk:
            session = get_object_or_404(Session.objects.select_related('submitter'), pk=session_pk)
            return session.can_user_access(request.user)
        else:
            return False

class IsEdtior(permissions.BasePermission):
    def has_permission(self, request, view):
        return teams.utils.is_editor(request.user)

class CanEditExam(permissions.BasePermission):
    def has_permission(self, request, view):
        exam_pk = request.query_params.get('exam_pk')

        if exam_pk:
            exam = get_object_or_404(Exam, pk=exam_pk)
            return exam.can_user_edit(request.user)
        else:
            return False

class CanAccessExam(permissions.BasePermission):
    def has_permission(self, request, view):
        exam_pk = request.query_params.get('exam_pk')
        question_pk = request.query_params.get('question_pk')

        if question_pk:
            return has_access_question(question_pk, request.user)
        elif exam_pk:
            exam = get_object_or_404(Exam, pk=exam_pk)
            return exam.can_user_access(request.user)
        else:
            return False

class AnswerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AnswerSerializer
    permission_classes = (HasSessionAccess,)

    def get_queryset(self):
        session_pk = self.request.query_params.get('session_pk')
        return Answer.objects.select_related('choice')\
                             .filter(session_id=session_pk,
                                     session__is_deleted=False)

class HighlightViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HighlightSerializer
    permission_classes = (HasSessionAccess,)

    def get_queryset(self):
        session_pk = self.request.query_params.get('session_pk')
        return Highlight.objects.filter(session_id=session_pk,
                                        session__is_deleted=False)

class MarkedQuestionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuestionIdSerializer
    permission_classes = (CanAccessExam,)

    def get_queryset(self):
        exam_pk = self.request.query_params.get('exam_pk')
        if exam_pk:
            pool =  Question.objects.filter(exam__pk=exam_pk)
        question_pk = self.request.query_params.get('question_pk')
        if question_pk:
            pool =  Question.objects.filter(pk=question_pk)

        return pool.filter(marking_users=self.request.user)\
                   .distinct()

class QuestionSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RevisionSummarySerializer
    permission_classes = (CanAccessExam,)

    def get_queryset(self):
        exam_pk = self.request.query_params.get('exam_pk')
        if exam_pk:
            exam = get_object_or_404(Exam, pk=exam_pk)
        selector = self.request.query_params.get('selector')
        question_pool = exam.question_set.undeleted()
        if selector.startswith('i-'):
            issue_pk = int(selector[2:])
            questions = exam.question_set.filter(issues__pk=issue_pk)
        elif selector.startswith('s-'):
            subject_pk = int(selector[2:])
            questions = exam.question_set.filter(subjects__pk=subject_pk)
        elif selector == 'all':
            questions = question_pool
        elif selector == 'assigned':
            questions = question_pool.filter(assigned_editor=self.request.user)
        elif selector == 'no_answer':
            questions = question_pool.unsolved()
        elif selector == 'no_issues':
            questions = question_pool.with_no_issues()
        elif selector == 'blocking_issues':
            questions = question_pool.with_blocking_issues()
        elif selector == 'nonblocking_issues':
            questions = question_pool.with_nonblocking_issues()
        elif selector == 'approved':
            questions = question_pool.with_approved_latest_revision()
        elif selector == 'pending':
            questions = question_pool.with_pending_latest_revision()
        elif selector == 'lacking_choices':
            questions = question_pool.lacking_choices()
        else:
            raise Http404

        return Revision.objects.select_related('question',
                                               'question__assigned_editor',
                                               'question__assigned_editor__profile')\
                               .filter(question__in=questions,
                                       is_last=True,
                                       is_deleted=False)\
                               .distinct()

class QuestionAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RevisionAssignmentSerializer

    def get_queryset(self):
        return Revision.objects.select_related('question',
                                               'question__exam',
                                               'question__exam__category',
                                               'question__assigned_editor',
                                               'question__assigned_editor__profile')\
                               .filter(question__assigned_editor=self.request.user,
                                       is_last=True)

class ActivityList(views.APIView):
    permission_classes = (IsEdtior,)

    def get(self, request, format=None):
        if request.user.is_superuser:
            exams = Exam.objects.all()
        else:
            exams = Exam.objects.filter(privileged_teams__members=request.user)

        try:
            count = int(request.query_params.get('count'))
        except (ValueError, TypeError):
            count = 50
        # Only superusers are allowed to exceed the limit.
        if count > 100 and not request.user.is_superuser:
            count = 50
        count_with_cursor = count + 1

        try:
            cursor = float(request.query_params.get('cursor'))
        except ValueError:
            raise exceptions.ParseError()
        except TypeError: # If no cursor is provided
            cursor = None

        target = request.query_params.get('target')
        if not target or \
           target not in ['count_since', 'results_since', 'results_until'] or \
           target in ['count_since', 'results_since'] and not cursor:
            raise exceptions.ParseError()

        recent_revisions = Revision.objects.select_related('question',
                                                           'question__exam',
                                                           'submitter',
                                                           'submitter__profile')\
                                           .filter(question__exam__in=exams,
                                                   is_deleted=False)\
                                           .order_by('-submission_date')
        recent_explanations = ExplanationRevision.objects.select_related('question',
                                                                         'question__exam', 
                                                                         'question__exam__category',
                                                                         'submitter',
                                                                         'submitter__profile')\
                                                         .filter(question__exam__in=exams,
                                                                 is_deleted=False)\
                                                         .order_by('-submission_date')
        recent_corrections = AnswerCorrection.objects.select_related('choice',
                                                                     'choice__revision',
                                                                     'choice__revision__question',
                                                                     'choice__revision__question__exam',
                                                                     'choice__revision__question__exam__category',
                                                                     'submitter',
                                                                     'submitter__profile')\
                                                     .filter(choice__revision__question__exam__in=exams)\
                                                     .order_by('-submission_date')
        recent_mnemonics = Mnemonic.objects.select_related('submitter',
                                                           'question',
                                                           'question__exam',
                                                           'question__exam__category',
                                                           'submitter__profile')\
                                           .filter(question__exam__in=exams,
                                                   is_deleted=False)\
                                           .order_by('-submission_date')
        recent_duplicates = DuplicateContainer.objects.select_related('reviser',
                                                                      'reviser__profile')\
                                              .filter(primary_question__exam__in=exams,
                                                      revision_date__isnull=False)\
                                              .exclude(status="PENDING")\
                                              .order_by('-revision_date')

        if cursor:
            cursor_datetime = datetime.datetime.fromtimestamp(cursor)
            cursor_datetime = timezone.make_aware(cursor_datetime, timezone.get_current_timezone())

        if target in ['results_since', 'count_since']:
            recent_revisions = recent_revisions.filter(submission_date__gt=cursor_datetime)
            recent_corrections = recent_corrections.filter(submission_date__gt=cursor_datetime)
            recent_explanations = recent_explanations.filter(submission_date__gt=cursor_datetime)
            recent_mnemonics = recent_mnemonics.filter(submission_date__gt=cursor_datetime)
            recent_duplicates = recent_duplicates.filter(revision_date__gt=cursor_datetime)
        elif target == 'results_until' and cursor:
            recent_revisions = recent_revisions.filter(submission_date__lte=cursor_datetime)
            recent_corrections = recent_corrections.filter(submission_date__lte=cursor_datetime)
            recent_explanations = recent_explanations.filter(submission_date__lte=cursor_datetime)
            recent_mnemonics = recent_mnemonics.filter(submission_date__lte=cursor_datetime)
            recent_duplicates = recent_duplicates.filter(revision_date__lte=cursor_datetime)

        if target == 'count_since':
            count = recent_revisions.count() + \
                    recent_corrections.count() + \
                    recent_explanations.count() + \
                    recent_mnemonics.count() + \
                    recent_duplicates.count()
            data = {'count': count}
        elif target in ['results_until', 'results_since']:
            activities = list(recent_revisions[:count_with_cursor]) + \
                         list(recent_explanations[:count_with_cursor]) + \
                         list(recent_corrections[:count_with_cursor]) + \
                         list(recent_mnemonics[:count_with_cursor]) + \
                         list(recent_duplicates[:count_with_cursor])

            data = {'next': None,
                    'results': []}

            def get_date(activity):
                if type(activity) is DuplicateContainer:
                    return activity.revision_date
                else:
                    return activity.submission_date

            def get_actor(activity):
                if type(activity) is DuplicateContainer:
                    return activity.reviser
                else:
                    return activity.submitter

            sorted_activities = sorted(activities, key=get_date, reverse=True)[:count_with_cursor]
            if len(sorted_activities) >= count_with_cursor:
                if target == 'results_until':
                    last_activity = sorted_activities[-1]
                elif target == 'results_since':
                    last_activity = sorted_activities[0]
                data['next'] = get_date(last_activity).timestamp()
                sorted_activities.remove(last_activity)
            for activity in sorted_activities:
                actor = get_actor(activity)
                summary = {'timestamp': get_date(activity).timestamp(),
                           'pk': activity.pk,
                           'type': activity.__class__.__name__.lower(),
                           'submitter': accounts.utils.get_user_credit(actor),
                           'submitter_is_editor': teams.utils.is_editor(actor),
                           'submitter_url': reverse('exams:list_contributions', args=(actor.pk,))}

                if type(activity) is Revision:
                    question = activity.question
                    summary['change_summary'] = activity.change_summary
                    summary['is_approved'] = activity.is_approved
                    summary['is_first'] = activity.is_first
                    summary['text'] = textwrap.shorten(activity.text, 70,
                                                       placeholder='...')
                    summary['url'] = activity.get_absolute_url()
                if type(activity) is ExplanationRevision:
                    question = activity.question
                    summary['is_first'] = activity.is_first
                    summary['url'] = activity.get_absolute_url()
                elif type(activity) is AnswerCorrection:
                    question = activity.choice.revision.question
                    summary['text'] = textwrap.shorten(activity.justification, 70,
                                                       placeholder='...')
                    summary['url'] = activity.choice.revision.question.get_absolute_url()
                elif type(activity) is Mnemonic:
                    question = activity.question
                    summary['text'] = textwrap.shorten(activity.text, 70,
                                                       placeholder='...')
                    summary['url'] = activity.question.get_absolute_url()
                elif type(activity) is DuplicateContainer:
                    if activity.status == 'KEPT':
                        kept_question = activity.get_kept_question()
                        if kept_question:
                            summary['kept_question'] = kept_question.pk
                    question = activity.primary_question
                    summary['container_pk'] = activity.pk
                    summary['involved_questions'] = activity.get_questions().values_list('pk', flat=True)
                    summary['status'] = activity.status

                summary['question_pk'] = question.pk
                summary['exam_name'] = question.exam.name
                summary['exam_url'] = question.exam.get_absolute_url()

                data['results'].append(summary)

        return Response(data)

class CorrectionList(views.APIView):
    permission_classes = (HasSessionOrQuestionAccess,)

    def get(self, request, format=None):
        session_pk = request.query_params.get('session_pk')
        question_pk = request.query_params.get('question_pk')

        if not session_pk and not question_pk:
            raise Http404

        choices_with_corrections = Choice.objects.select_related('answer_correction',
                                                                 'revision',
                                                                 'revision__question')\
                                                 .filter(revision__best_of__isnull=False,
                                                         answer_correction__isnull=False)

        if session_pk:
            choices_with_corrections = choices_with_corrections.filter(revision__question__session__pk=session_pk)
        elif question_pk:
            choices_with_corrections = choices_with_corrections.filter(revision__question__pk=question_pk)

        data = []
        template = get_template("exams/partials/show_answer_correction.html")
        for choice in choices_with_corrections:            
            context = {'choice': choice, 'user': request.user}
            html = template.render(context)
            data.append({'question_id': choice.revision.question.pk,
                         'choice_id': choice.pk,
                         'html': html})

        return Response(data)

class CustomPagination(pagination.CursorPagination):
    ordering = 'id'
    page_size = 50

class SuggestedChangeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SuggestedChangeSerializer
    pagination_class = CustomPagination
    permission_classes = (CanEditExam,)

    def get_queryset(self):
        exam_pk = self.request.query_params.get('exam_pk')

        if not exam_pk:
            raise Http404

        exam = get_object_or_404(Exam, pk=exam_pk)

        return exam.get_pending_suggested_changes()

class DuplicateContainerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DuplicateContainerSerializer
    pagination_class = CustomPagination
    permission_classes = (CanEditExam,)

    def get_queryset(self):
        exam_pk = self.request.query_params.get('exam_pk')

        if not exam_pk:
            raise Http404

        exam = get_object_or_404(Exam, pk=exam_pk)

        return exam.get_pending_duplicates()
