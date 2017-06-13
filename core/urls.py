from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^ajax/get_users$', views.UserAutocomplete.as_view(), name='user_autocomplete'),
    url(r'^$', views.show_index, name="index"),
]
