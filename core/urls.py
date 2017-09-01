from django.conf.urls import url
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    url(r'^ajax/get_users$', views.UserAutocomplete.as_view(), name='user_autocomplete'),
    url(r'^about/$', views.show_about, name="about"),
    url(r'^$', views.show_index, name="index"),
]
