from django.contrib import admin
from . import models

class TeamAdmin(admin.ModelAdmin):
    autocomplete_fields = ['members', 'exams']
    list_display = ['name', 'code_name', 'get_member_count']
    search_fields = ['name', 'code_name']

admin.site.register(models.Team, TeamAdmin)
