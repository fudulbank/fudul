from django.contrib import admin
from . import models

class CoreMemberAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['name', 'role']

class DonationMessageAdmin(admin.ModelAdmin):
    search_fields = ['text']
    list_display = ['pk', 'text', 'is_enabled']

admin.site.register(models.CoreMember, CoreMemberAdmin)
admin.site.register(models.DonationMessage, DonationMessageAdmin)
