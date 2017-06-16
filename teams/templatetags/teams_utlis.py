from django import template
from teams import utils

register = template.Library()

@register.filter
def is_editor(user):
    return is_editor(user)