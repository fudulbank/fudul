from django import forms
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import authenticate
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

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            self.user_cache = authenticate(self.request, identification=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
    
class EditorAdmin(admin.sites.AdminSite):
    login_form = EditorAuthenticationForm

    def has_permission(self, request):
        return teams.utils.is_editor(request.user) or \
            request.user.is_superuser

class SubjectInline(admin.TabularInline):
    model= models.Subject
    extra = 0
    readonly_fields = ['is_deleted']

class ExamDateInline(admin.TabularInline):
    model= models.ExamDate
    extra = 0

class SourceInline(admin.TabularInline):
    model= models.Source
    extra = 0

class EditorModelAdmin(admin.ModelAdmin):
    def has_module_permission(self, request, obj=None):
        return teams.utils.is_editor(request.user) or \
               request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return teams.utils.is_editor(request.user) or \
               request.user.is_superuser
    
class ExamAdmin(EditorModelAdmin):
    search_fields = ['name', 'category__name']
    list_display = ['__str__', 'category']
    list_filter = ['category']
    inlines = [SubjectInline, ExamDateInline]
    readonly_fields = ['is_deleted']

class CategoryAdmin(EditorModelAdmin):
    search_fields = ['name']
    inlines = [SourceInline]

class SuggestedChangeAdmin(admin.ModelAdmin):
    readonly_fields = ['revision', 'reviser', 'revision_date']

editor_site = EditorAdmin("editor_admin")

admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.Exam, ExamAdmin)
admin.site.register(models.ExamType)
admin.site.register(models.Issue)
admin.site.register(models.Rule)
admin.site.register(models.Session)
admin.site.register(models.SuggestedChange, SuggestedChangeAdmin)
editor_site.register(models.Category, CategoryAdmin)
editor_site.register(models.Exam, ExamAdmin)
