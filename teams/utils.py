def is_editor(user):
    if not user.is_authenticated:
        return False

    return user.is_superuser or \
        hasattr(user, 'profile') and user.profile.is_editor

def is_examiner(user):
    if not user.is_authenticated:
        return False

    return user.is_superuser or \
        hasattr(user, 'profile') and user.profile.is_examiner
