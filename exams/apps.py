from django.apps import AppConfig
from django.core.cache import cache

class ExamsConfig(AppConfig):
    name = 'exams'
    verbose_name = 'Fudul exams'

    def ready(self):
        from . import signals
        from .models import Category

        for category in Category.objects.select_related('parent_category'):
            category.set_slug_cache()
