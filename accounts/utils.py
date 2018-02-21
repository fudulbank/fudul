from django.core.exceptions import ObjectDoesNotExist
import teams.utils


def get_user_representation(user, with_email=True, with_nickname=False):
    if not user:
        return
    if hasattr(user, 'profile'):
        full_name = user.profile.get_full_name()
    elif user.is_superuser:
        full_name = user.username
    else:
        full_name = None

    if full_name:
        addition = []
        if with_email:
            addition.append(user.email)
        if with_nickname and \
           hasattr(user, 'profile') and \
           user.profile.nickname:
            addition.append(user.profile.nickname)

        if addition:
            result = "%s (%s)" % (full_name, "; ".join(addition))
        else:
            result = full_name
    else:
        result = user.email

    return result 

def get_user_full_name(user):
    full_name = ''

    if user.is_authenticated() and hasattr(user, 'profile'):
        full_name = user.profile.get_full_name()

    return full_name

def get_user_institution(user):
    institution = ''

    if user.is_authenticated() and hasattr(user, 'profile'):
        institution = user.profile.institution

    return institution

def get_user_college(user):
    college = None

    if user.is_authenticated() and hasattr(user, 'profile'):
        college = user.profile.college

    return college


def get_user_credit(contributing_user, viewing_user=None, full=False):
    if not contributing_user:
        return None

    if hasattr(contributing_user, 'profile'):
        profile = contributing_user.profile
    else:
        profile = None

    if not full:
        if viewing_user and \
           viewing_user.is_authenticated() and \
           teams.utils.is_editor(viewing_user):
            full = True
        else:
            full = False

    if profile:
        if profile.display_full_name == 'Y' or full:
            credit =get_user_full_name(contributing_user)
            if profile.nickname:
                credit += " ({})".format(profile.nickname)
        elif profile.display_full_name == 'N':
            if profile.nickname:
                credit = profile.nickname
            else:
                credit = contributing_user.username
    else:  # not profile
        credit = contributing_user.username
    return credit


