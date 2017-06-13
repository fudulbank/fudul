from .models import Team

def is_editors_team_member(user):
    if not user.is_authenticated():
        return False
    if Team.members.filter(team_memberships__access='editors',pk=user.pk) or user.is_superuser():
        return True

