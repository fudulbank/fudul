from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import urlize as urlize_impl

register = template.Library()

@register.filter
@stringfilter
def urlize_target_blank(value, autoescape=None):
    return mark_safe(urlize_impl(value, nofollow=True, autoescape=autoescape).replace('<a', '<a rel="noopener" target="_blank"'))
