from django.contrib import admin
from .models import Category,Exam,Source
from django.contrib import admin
from accounts.admin import editor_site
from .models import Year,Exam,Subject,Question,Choice,Revision

class SubjectInline(admin.TabularInline):
    model= Subject
    extra = 1

class ChoiceInline(admin.TabularInline):
    model= Choice
    extra = 0

# class QuestionAdmin(admin.ModelAdmin):
#     list_display = [ 'figure']
#     search_fields = ['text', 'explanation']
#     list_filter = ['subject','source','subject',]

admin.site.register(Year)
admin.site.register(Exam)
admin.site.register(Subject)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(Revision)

editor_site.register(Subject)
# editor_site.register(Question, QuestionAdmin)

admin.site.register(Category)
admin.site.register(Source)