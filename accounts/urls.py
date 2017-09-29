from django.conf.urls import url, include
from . import views , forms
from userena import views as userenaviews

urlpatterns = [
    url(r'^details$', views.get_institution_details, name='get_institution_details'),
    url(r'^signup/$', views.signup, name="signup"),
    url(r'^(?P<username>[\.\w-]+)/edit/$', userenaviews.profile_edit,{'edit_profile_form': forms.CustomEditProfileForm}, name='userena_profile_edit'),
    url(r'', include('userena.urls')),
]
