from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from . import models

class CoreMemberAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['name', 'role']

class DonationMessageAdmin(admin.ModelAdmin):
    search_fields = ['text']
    list_display = ['pk', 'text', 'is_enabled', 'get_preview']
    def get_preview(self, obj):
        index_url = reverse('index')
        return mark_safe(f"<a href=\"{index_url}?donation_message_pk={obj.pk}\">Preview</a>")
    get_preview.short_description = 'Preview'

admin.site.register(models.CoreMember, CoreMemberAdmin)
admin.site.register(models.DonationMessage, DonationMessageAdmin)
