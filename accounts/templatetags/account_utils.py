from django import template

register = template.Library()

@register.filter
def is_user_allowed_to_institution(user, institution):
    return institution.is_user_allowed(user)
