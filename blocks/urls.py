from django.conf.urls import url, include
from blocks import views

urlpatterns =[
    url(r'^$', views.list_meta_categories, name='list_meta_categories'),
    url(r'^ajax/subjects$', views.SubjectAutocomplete.as_view(), name='subject_autocomplete'),
    url(r'^ajax/sources$', views.SourceAutocomplete.as_view(), name='source_autocomplete'),
    url(r'^ajax/revisions/(?P<revision_pk>\d+)$', views.show_question, name='show_question'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/add/$', views.add_question, name='add_question'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/list/$', views.list_questions, name='list_questions'),
    url(r'^(?P<slugs>[/\d\w\-]+)/$',views.show_category, name='show_category'),
    url(r'^revisions/(?P<pk>\d+)/$', views.list_revisions, name='list_revisions'),
]
