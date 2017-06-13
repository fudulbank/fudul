from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.models import User
from .models import Batch, College, Institution, Profile
from exams.models import Category

class EditorAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active and \
           not utils.is_editor(user):
            raise forms.ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login',
                params={'username': self.username_field.verbose_name}
                )

class EditorAdmin(admin.sites.AdminSite):
    login_form = EditorAuthenticationForm

    def has_permission(self, request):
        return utils.is_editor(request.user) or \
            request.user.is_superuser

class BatchInline(admin.StackedInline):
    model = Batch
    extra = 1

class CollegeAdmin(admin.ModelAdmin):
    search_fields = ['name', 'institution__name']
    list_display = ['name', 'institution', 'get_user_count']
    list_filter = ['institution']
    inlines = [BatchInline]

    def get_user_count(self, obj):
        return obj.profile_set.count()

class InstitutionAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['name', 'get_user_count']

    def get_user_count(self, obj):
        return User.objects.filter(profile__college__institution=obj).count()

editor_site = EditorAdmin("Editor Admin")
admin.site.register(College, CollegeAdmin)
admin.site.register(Institution, InstitutionAdmin)
editor_site.register(College, CollegeAdmin)
editor_site.register(Institution, InstitutionAdmin)
