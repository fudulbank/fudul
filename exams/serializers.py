from exams.models import Answer, Session
from rest_framework import serializers, viewsets, permissions
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404


# Serializers define the API representation.
class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ('question_id', 'choice_id')

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

# ViewSets define the view behavior.
class AnswerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AnswerSerializer
    permission_classes = (HasSessionAccess,)

    def get_queryset(self):
        session_pk = self.request.query_params.get('session_pk')
        return Answer.objects.filter(session_id=session_pk,
                                     session__is_deleted=False)
