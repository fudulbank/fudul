from exams.models import *
from accounts.utils import get_user_credit
from rest_framework import serializers, viewsets, permissions
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import truncatewords, linebreaksbr

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ('question_id', 'choice_id')

class QuestionIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ('id',)

class RevisionSummarySerializer(serializers.ModelSerializer):
    question = QuestionIdSerializer(read_only=True)
    summary = serializers.SerializerMethodField()
    assigned_editor = serializers.SerializerMethodField()

    def get_assigned_editor(self, obj):
        return get_user_credit(obj.question.assigned_editor)

    def get_summary(self, obj):
        return linebreaksbr(truncatewords(obj.text, 70))

    class Meta:
        model = Revision
        fields = ('question', 'summary', 'submission_date', 'assigned_editor')

class RevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revision
        fields = ('id', 'question_id')

class HighlightSerializer(serializers.ModelSerializer):
    revision = RevisionSerializer(read_only=True)

    class Meta:
        model = Highlight
        fields = ('revision', 'highlighted_text', 'stricken_choices')

class HasSessionAccess(permissions.BasePermission):
    def has_permission(self, request, view):
        session_pk = request.query_params.get('session_pk')
        if not session_pk:
            return False

        if request.user.is_superuser:
            return True
        else:
            session = get_object_or_404(Session, pk=session_pk)
            return session.submitter == request.user

class HasExamAccess(permissions.BasePermission):
    def has_permission(self, request, view):
        exam_pk = request.query_params.get('exam_pk')
        if not exam_pk:
            return False

        if request.user.is_superuser:
            return True
        else:
            exam = get_object_or_404(Exam, pk=exam_pk)
            return exam.can_user_access(request.user)

class AnswerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AnswerSerializer
    permission_classes = (HasSessionAccess,)

    def get_queryset(self):
        session_pk = self.request.query_params.get('session_pk')
        return Answer.objects.filter(session_id=session_pk,
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
    permission_classes = (HasExamAccess,)

    def get_queryset(self):
        exam_pk = self.request.query_params.get('exam_pk')
        return Question.objects.filter(exam__pk=exam_pk,
                                       marking_users=self.request.user)\
                               .distinct()


class QuestionSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RevisionSummarySerializer
    permission_classes = (HasExamAccess,)

    def get_queryset(self):
        exam_pk = self.request.query_params.get('exam_pk')
        exam = get_object_or_404(Exam, pk=exam_pk)
        selector = self.request.query_params.get('selector')
        question_pool = exam.question_set.all()
        try:
            issue_pk = int(selector)
        except ValueError:
            if selector == 'all':
                questions = question_pool
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
        else:
            issue = get_object_or_404(Issue, pk=issue_pk)
            questions = exam.question_set.undeleted()\
                                         .filter(issues=issue)

        return Revision.objects.select_related('question',
                                               'question__assigned_editor',
                                               'question__assigned_editor__profile')\
                               .filter(question__in=questions,
                                       is_last=True)\
                               .distinct()
