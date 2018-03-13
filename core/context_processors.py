from django.conf import settings
from exams.models import Session, Revision, Category
import exams.utils
import teams.utils


def universal_context(request):
    context = {'CACHE_PERIODS': settings.CACHE_PERIODS}
    if request.user.is_authenticated():
        is_any_editor = teams.utils.is_editor(request.user)
        meta_categories = Category.objects.meta()
        context.update({'is_any_editor': is_any_editor,
                        'meta_categories': meta_categories})
    return context
