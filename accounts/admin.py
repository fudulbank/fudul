from django.contrib import admin
from django.contrib.auth.models import User

from core.utils import BASIC_SEARCH_FIELDS
from exams.admin import editor_site
from exams.models import Category
from userena.admin import UserenaAdmin
from .models import Batch, College, Institution, Profile
from . import utils


class ProfileInline(admin.StackedInline):
    model = Profile
    max_num = 1
    extra = 0

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

class UserAdmin(UserenaAdmin):
    ordering = ['-date_joined']
    change_form_template = 'loginas/change_form.html'
    inlines = [ProfileInline,]
    actions = ['make_active']
    search_fields = [field.replace('user__', '') for field in BASIC_SEARCH_FIELDS]
    list_display = ('pk', 'get_user_representation', 'email',
                    'is_active',
                    'date_joined')

    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    def get_user_representation(self, obj):
        return utils.get_user_representation(obj, with_email=False)
    get_user_representation.short_description = 'Name'

admin.site.unregister(User)
admin.site.unregister(Profile)
admin.site.register(User, UserAdmin)
admin.site.register(College, CollegeAdmin)
admin.site.register(Institution, InstitutionAdmin)
editor_site.register(User, UserAdmin)
editor_site.register(College, CollegeAdmin)
editor_site.register(Institution, InstitutionAdmin)
