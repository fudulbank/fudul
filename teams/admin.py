from dal import autocomplete
from django.contrib import admin
from . import forms 
from . import models

class TeamAdmin(admin.ModelAdmin):
    form = forms.TeamForm
    list_display = ['name', 'code_name', 'get_member_count']
    search_fields = ['name', 'code_name']

admin.site.register(models.Team, TeamAdmin)
