from django import template
from accounts import utils

import teams.utils


register = template.Library()

@register.filter
def is_user_allowed_to_institution(user, institution):
    return institution.is_user_allowed(user)

@register.simple_tag
def get_user_representation(user, with_email=False, with_nickname=True):
    return utils.get_user_representation(user, with_email=with_email,
                                         with_nickname=with_nickname)

@register.filter
def get_user_credit(contributing_user, viewing_user=None):
    if not contributing_user:
        return None

    if hasattr(contributing_user, 'profile'):
        profile = contributing_user.profile
    else:
        profile = None

    if viewing_user and \
       viewing_user.is_authenticated() and \
       teams.utils.is_editor(viewing_user):
        full = True
    else:
        full = False

    if profile:
        if profile.display_full_name == 'Y' or full:
            credit = utils.get_user_full_name(contributing_user)
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
