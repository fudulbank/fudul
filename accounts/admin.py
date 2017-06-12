from django.contrib import admin
from django.contrib.auth.models import User
from .models import Batch, College, Institution, Profile


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

admin.site.register(College, CollegeAdmin)
admin.site.register(Institution, InstitutionAdmin)
