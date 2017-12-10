from django.conf.urls import url
from django.views.generic import TemplateView
from . import views
from exams import views as exam_views

urlpatterns = [
    url(r'^ajax/get_users$', views.UserAutocomplete.as_view(), name='user_autocomplete'),

    url(r'^indicators/$', views.show_indicator_index, name="show_indicator_index"),
    url(r'^indicators/teams/(?P<pk>\d+)/$', views.show_team_indicators, name='show_team_indicators'),
    url(r'^indicators/colleges/(?P<pk>\d+)/$', views.show_college_indicators, name='show_college_indicators'),

    url(r'^indicators/categories/$', exam_views.list_meta_categories, {'indicators': True}, name='list_category_indicators'),
    url(r'^indicators/categories/(?P<slugs>[/\d\w\-]+)/$', exam_views.show_category, {'indicators': True}, name='show_category_indicators'),

    url(r'^about/$', views.show_about, name="about"),
    url(r'^help/$', TemplateView.as_view(template_name="help.html"), name="help"),
    url(r'^$', views.show_index, name="index"),
]
