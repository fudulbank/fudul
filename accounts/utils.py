from django.core.exceptions import ObjectDoesNotExist

def get_user_institution(user):
    if not user.is_authenticated() or user.is_superuser:
        return ''
    try:
        institution= user.profile.institution
    except (ObjectDoesNotExist, AttributeError):
        institution =''
    return institution

def get_user_college(user):
    if not user.is_authenticated():
        return ''
    try:
        college= user.profile.college
    except (ObjectDoesNotExist, AttributeError):
        college =''
    return college
