from django.core.exceptions import ObjectDoesNotExist

def get_user_full_name(user):
    if not user.is_authenticated():
        return ''
    try:
        full_name = user.profile.get_full_name()
    except (ObjectDoesNotExist, AttributeError):
        full_name =''
    return full_name

def get_user_institution(user):
    if not user.is_authenticated():
        return ''
    try:
        institution = user.profile.institution
    except (ObjectDoesNotExist, AttributeError):
        institution =''
    return institution

def get_user_college(user):
    if not user.is_authenticated():
        return ''
    try:
        college = user.profile.college
    except (ObjectDoesNotExist, AttributeError):
        college =''
    return college


