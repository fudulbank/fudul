from django.apps import AppConfig


class ExamsConfig(AppConfig):
    name = 'exams'
    verbose_name = 'Fudul exams'

    def ready(self):
        from . import signals
