import teams.utils
import exams.utils
from exams.models import Session, Revision, Category


def universal_context(request):
    if request.user.is_authenticated():
        is_any_editor = teams.utils.is_editor(request.user)
        user_session_count = Session.objects\
                                    .filter(submitter=request.user)\
                                    .count()
        privileged_exams = exams.utils.get_user_privileged_exams(request.user)
        pending_revision_count = Revision.objects.undeleted()\
                                                 .filter(question__exam__in=privileged_exams)\
                                                 .count()
        meta_categories = Category.objects.meta()
        return {'is_any_editor': is_any_editor,
                'meta_categories': meta_categories,
                'pending_revision_count': pending_revision_count,
                'user_session_count': user_session_count}
    else:
        return {}
