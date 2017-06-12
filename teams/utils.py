from .models import Team

def is_team_member(user):
    if not user.is_authenticated():
        return False
    return Team.members.filter(pk=user.pk)