from django.conf.urls import url
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    url(r'^ajax/get_users$', views.UserAutocomplete.as_view(), name='user_autocomplete'),
    url(r'^privileged/(?P<path>.+)$', views.get_privileged_file, name='get_privileged_file'),

    url(r'^notifications/delete_all$', views.mark_all_notifications_as_deleted, name='mark_all_notifications_as_deleted'),

    url(r'^indicators/$', views.show_indicator_index, name="show_indicator_index"),
    url(r'^indicators/teams/(?P<pk>\d+)/$', views.show_team_indicators, name='show_team_indicators'),
    url(r'^indicators/exams/(?P<pk>\d+)/$', views.show_exam_indicators, name='show_exam_indicators'),
    url(r'^indicators/colleges/(?P<pk>\d+)/$', views.show_college_indicators, name='show_college_indicators'),

    url(r'^about/$', views.show_about, name="about"),
    url(r'^help/$', TemplateView.as_view(template_name="help.html"), name="help"),
    url(r'^$', views.show_index, name="index"),
]
