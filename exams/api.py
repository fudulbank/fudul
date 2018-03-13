from exams.models import *
from accounts.utils import get_user_credit
from rest_framework import serializers, views, viewsets, permissions, pagination
from rest_framework.response import Response
from django.template.loader import get_template
from django.http import HttpResponseBadRequest, Http404
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import truncatewords, linebreaksbr


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ('question_id', 'choice_id')

class RulesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = ('regex_pattern', 'regex_replacement', 'scope')

class ChoiceTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ('id', 'text', 'is_right')

class RevisionTextSerializer(serializers.ModelSerializer):
    choice_set = ChoiceTextSerializer(read_only=True, many=True)

    class Meta:
        model = Revision
        fields = ('id', 'question_id', 'text', 'choice_set')

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

class HasExamAccess(permissions.BasePermission):
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
        if exam_pk:
            pool =  Question.objects.filter(exam__pk=exam_pk)
        question_pk = self.request.query_params.get('question_pk')
        if question_pk:
            pool =  Question.objects.filter(pk=question_pk)

        return pool.filter(marking_users=self.request.user)\
                   .distinct()

class QuestionSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RevisionSummarySerializer
    permission_classes = (HasExamAccess,)

    def get_queryset(self):
        exam_pk = self.request.query_params.get('exam_pk')
        if exam_pk:
            exam = get_object_or_404(Exam, pk=exam_pk)
        selector = self.request.query_params.get('selector')
        question_pool = exam.question_set.all()
        if selector.startswith('i-'):
            issue_pk = int(selector[2:])
            questions = exam.question_set.undeleted()\
                                         .filter(issues__pk=issue_pk)
        elif selector.startswith('s-'):
            subject_pk = int(selector[2:])
            questions = exam.question_set.undeleted()\
                                         .filter(subjects__pk=subject_pk)
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
                                       is_last=True)\
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

class SuggestedChangePagination(pagination.CursorPagination):
    ordering = 'id'
    page_size = 50

class SuggestedChangeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SuggestedChangeSerializer
    pagination_class = SuggestedChangePagination

    def get_queryset(self):
        exam_pk = self.request.query_params.get('exam_pk')

        if not exam_pk:
            raise Http404

        exam = get_object_or_404(Exam, pk=exam_pk)

        return exam.get_pending_suggested_changes()
