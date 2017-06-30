from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from . import models
import teams.utils

class EditorAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active and \
           not teams.utils.is_editor(user):
            raise forms.ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login',
                params={'username': self.username_field.verbose_name}
                )

class EditorAdmin(admin.sites.AdminSite):
    login_form = EditorAuthenticationForm

    def has_permission(self, request):
        return teams.utils.is_editor(request.user) or \
            request.user.is_superuser

class SubjectInline(admin.TabularInline):
    model= models.Subject
    extra = 0
    readonly_fields = ['is_deleted']

class SourceInline(admin.TabularInline):
    model= models.Source
    extra = 0

class ExamAdmin(admin.ModelAdmin):
    search_fields = ['name', 'category__name']
    list_display = ['__str__', 'category']
    list_filter = ['category']
    inlines = [SubjectInline]
    readonly_fields = ['is_deleted']

class CategoryAdmin(admin.ModelAdmin):
    search_fields = ['name']
    inlines = [SourceInline]


editor_site = EditorAdmin("editor_admin")

admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.Exam, ExamAdmin)
admin.site.register(models.Status)
admin.site.register(models.Session)

editor_site.register(models.Category, CategoryAdmin)
editor_site.register(models.Exam, ExamAdmin)
