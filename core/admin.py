from django.contrib import admin
from . import models

class CoreMemberAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['name', 'role']

admin.site.register(models.CoreMember, CoreMemberAdmin)
