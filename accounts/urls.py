from django.conf.urls import url, include
from . import views


urlpatterns = [
    url(r'^details$', views.get_institution_details, name='get_institution_details'),
    url(r'^signup/$', views.signup, name="signup"),
    url(r'', include('userena.urls')),
]
