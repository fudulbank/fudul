from django import template
from accounts import utils


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
    return utils.get_user_credit(contributing_user, viewing_user)
