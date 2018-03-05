from django.conf.urls import url, include
from django.core.urlresolvers import reverse_lazy
from . import views , forms
from userena import views as userena_views

urlpatterns = [
    url(r'^details$', views.get_institution_details, name='get_institution_details'),
    url(r'^signup/$', views.signup, name="signup"),

    # Override userena's activate view to change the success_url
    url(r'^activate/(?P<activation_key>\w+)/$',
       userena_views.activate,
       {'success_url': reverse_lazy('index')},
       name='userena_activate'),

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
