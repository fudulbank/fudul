from django.contrib import admin
from blocks.models import Year,Block,Subject,Question,Choice
# Register your models here.


class ChoiceInline(admin.TabularInline):
    model= Choice
    extra=0


class QuestionAdmin(admin.ModelAdmin):
    inlines=[ChoiceInline]
    list_display = ['subject','batch', 'type', 'text', 'explanation', 'figure']
    list_filter = ['subject']

admin.site.register(Year)
admin.site.register(Block)
admin.site.register(Subject)
admin.site.register(Question, QuestionAdmin)
