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
    list_display = ['__str__', 'get_user_count', 'get_question_count']
    list_filter = ['was_announced']
    inlines = [SubjectInline, ExamDateInline]
    readonly_fields = ['is_deleted']

    def get_question_count(self, obj):
        return obj.question_set.undeleted().count()
    get_question_count.short_description = '# questions'

class CategoryAdmin(EditorModelAdmin):
    search_fields = ['name']
    inlines = [SourceInline]

class RuleForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(RuleForm, self).__init__(*args, **kwargs)
        # Do not trim initial and tailing white spaces.
        self.fields['regex_pattern'].strip = False
        self.fields['regex_replacement'].strip = False

    class Meta:
        model = models.Rule
        fields = '__all__'
    
class RuleAdmin(admin.ModelAdmin):
    form = RuleForm
    search_fields = ['regex_pattern', 'regex_replacement']
    list_display = ['pk', 'regex_pattern', 'regex_replacement',
                    'scope', 'get_count', 'get_percentage',
                    'is_disabled', 'is_automatic']
    list_filter = ['scope', 'is_disabled', 'is_automatic']
    actions = ['mark_automatic', 'unmark_automatic', 'mark_disabled',
               'unmark_disabled']

    def get_count(self, obj):
        return models.SuggestedChange.objects.filter(rules=obj)\
                                             .distinct()\
                                             .count()
    get_count.short_description = "Suggested change #"

    def get_percentage(self, obj):
        if obj.is_automatic:
            return "Automatic"

        resolved = models.SuggestedChange.objects.filter(rules=obj)\
                                                 .exclude(status='PENDING')\
                                                 .distinct()\
                                                 .count()
        if resolved:
            kept = models.SuggestedChange.objects.filter(rules=obj, status='KEPT')\
                                                 .distinct()\
                                                 .count()
            percentage = kept / resolved * 100
            return "{0:.2f}%".format(percentage)
        else:
            return "N/A"
    get_percentage.short_description = "Approved changes %"

    def mark_disabled(self, request, queryset):
        queryset.update(is_disabled=True)

    def mark_automatic(self, request, queryset):
        queryset.update(is_automatic=True)

    def unmark_disabled(self, request, queryset):
        queryset.update(is_disabled=False)

    def unmark_automatic(self, request, queryset):
        queryset.update(is_automatic=False)

class SuggestedChangeAdmin(admin.ModelAdmin):
    readonly_fields = ['revision', 'reviser', 'revision_date']

class SessionThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_count'] 
    def get_count(self, obj):
        return obj.profile_set.count()
    get_count.short_description = "# users"

editor_site = EditorAdmin("editor_admin")

admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.Exam, ExamAdmin)
admin.site.register(models.ExamType)
admin.site.register(models.Issue)
admin.site.register(models.Rule, RuleAdmin)
admin.site.register(models.Session)
admin.site.register(models.SessionTheme, SessionThemeAdmin)
admin.site.register(models.SuggestedChange, SuggestedChangeAdmin)
editor_site.register(models.Category, CategoryAdmin)
editor_site.register(models.Exam, ExamAdmin)
