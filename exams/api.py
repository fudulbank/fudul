from exams.models import *
from rest_framework import serializers, viewsets, permissions
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ('question_id', 'choice_id')

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