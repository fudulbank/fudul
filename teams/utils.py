from exams.models import Exam

def is_editor(user):
    if not user.is_authenticated():
        return False

    if user.is_superuser or \
       user.team_memberships.exclude(categories__isnull=True)\
                            .exists():
        return True
    else:
        return False
