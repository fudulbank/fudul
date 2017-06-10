from django.contrib import admin
from accounts.admin import editor_site  
from .models import Year,Block,Subject,Question,Choice

class SubjectInline(admin.TabularInline):
    model= Subject
    extra = 1

class ChoiceInline(admin.TabularInline):
    model= Choice
    extra = 0

class QuestionAdmin(admin.ModelAdmin):
    inlines=[ChoiceInline]
    list_display = ['subject','batch', 'type', 'text', 'explanation', 'figure']
    search_fields = ['text', 'explanation']
    list_filter = ['subject']

admin.site.register(Year)
admin.site.register(Block)
admin.site.register(Subject)
admin.site.register(Question, QuestionAdmin)
editor_site.register(Subject)
editor_site.register(Question, QuestionAdmin)
