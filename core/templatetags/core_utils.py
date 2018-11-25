from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import urlize as urlize_impl
from core.models import DonationMessage


register = template.Library()

@register.filter
@stringfilter
def urlize_target_blank(value, autoescape=None):
    return mark_safe(urlize_impl(value, nofollow=True, autoescape=autoescape).replace('<a', '<a rel="noopener" target="_blank"'))

@register.simple_tag
def get_donation_message():
    random_message = DonationMessage.objects.filter(is_enabled=True)\
                                            .order_by('?').first()
    return random_message
