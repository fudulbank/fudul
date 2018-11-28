from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import urlize as urlize_impl
from constance import config
from core.models import DonationMessage


register = template.Library()

@register.filter
@stringfilter
def urlize_target_blank(value, autoescape=None):
    return mark_safe(urlize_impl(value, nofollow=True, autoescape=autoescape).replace('<a', '<a rel="noopener" target="_blank"'))

@register.simple_tag
def get_donation_message(pk=None):
    if pk:
        try:
            donation_message = DonationMessage.objects.get(pk=pk)
        except DonationMessage.DoesNotExist:
            return None
    else:
        donation_message = DonationMessage.objects.filter(is_enabled=True)\
                                                  .order_by('?').first()
    return donation_message

@register.simple_tag
def get_donation_target_percentage():
    return round(config.WF_CURRENT_BALANCE / config.DONATION_TARGET * 100, 1)
