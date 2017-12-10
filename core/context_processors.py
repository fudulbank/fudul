import teams.utils
import exams.utils
from exams.models import Session, Revision, Category


def universal_context(request):
    if request.user.is_authenticated():
        is_any_editor = teams.utils.is_editor(request.user)
        meta_categories = Category.objects.meta()
        return {'is_any_editor': is_any_editor,
                'meta_categories': meta_categories}
    else:
        return {}
