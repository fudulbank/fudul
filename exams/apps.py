from django.apps import AppConfig
from django.core.cache import cache
from django.db import OperationalError

class ExamsConfig(AppConfig):
    name = 'exams'
    verbose_name = 'Fudul exams'

    def ready(self):
        from . import signals
        from .models import Category

        # Don't fail on new installations (before Category table is
        # created in the database)
        try:
            for category in Category.objects.select_related('parent_category'):
                category.set_slug_cache()
        except OperationalError:
            pass
