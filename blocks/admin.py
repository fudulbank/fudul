from django.contrib import admin
from accounts.admin import editor_site
from . import models

class SubjectInline(admin.TabularInline):
    model= models.Subject
    extra = 0

class ExamAdmin(admin.ModelAdmin):
    search_fields = ['name', 'category__name']
    inlines = [SubjectInline]

class CategoryAdmin(admin.ModelAdmin):
    search_fields = ['name']

admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.Exam, ExamAdmin)

editor_site.register(models.Category, CategoryAdmin)
editor_site.register(models.Exam, ExamAdmin)

