from django.apps import AppConfig
from django.db.models.signals import post_save
from . import signals

class TeamsConfig(AppConfig):
    name = 'teams'
    verbose_name = 'Fudul teams'

    def ready(self):
        post_save.connect(signals.mark_editors, sender="teams.Team", dispatch_uid="mark_editors")
        post_save.connect(signals.mark_examiners, sender="teams.Team", dispatch_uid="mark_examiners")
