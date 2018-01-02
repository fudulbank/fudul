from django.conf.urls import url, include
from . import views , forms
from userena import views as userenaviews

urlpatterns = [
    url(r'^details$', views.get_institution_details, name='get_institution_details'),
    url(r'^signup/$', views.signup, name="signup"),
    url(r'^(?P<username>[\.\w-]+)/edit/$', views.edit_profile, name='userena_profile_edit'),
    # Change personal_email and confirm it
    url(r'^(?P<username>[\@\.\w-]+)/personal_email/$',
        views.personal_email_change,
        name='personal_email_change'),
    url(r'^confirm-personal-email/(?P<confirmation_key>\w+)/$',
        views.personal_email_confirm,
        name='personal_email_confirm'),
    url(r'', include('userena.urls')),
]
