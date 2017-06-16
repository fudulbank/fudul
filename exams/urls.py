from django.conf.urls import url, include
from exams import views

urlpatterns =[
    url(r'^$', views.list_meta_categories, name='list_meta_categories'),
    url(r'^ajax/subjects$', views.SubjectAutocomplete.as_view(), name='subject_autocomplete'),
    url(r'^ajax/sources$', views.SourceAutocomplete.as_view(), name='source_autocomplete'),
    url(r'^ajax/revisions/(?P<revision_pk>\d+)$', views.show_question, name='show_question'),
    url(r'^ajax/(?P<exam_pk>\d+)$', views.handle_question, name='handle_question'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/add/$', views.add_question, name='add_question'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/list/$', views.list_questions, name='list_questions'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/questions/(?P<pk>\d+)/$', views.list_revisions, name='list_revisions'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/questions/(?P<pk>\d+)/edit/$', views.submit_revision,name='submit_revision'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/questions/status/list/$', views.list_question_per_status,name='list_question_per_status'),
    url(r'^(?P<slugs>[/\d\w\-]+)/$', views.show_category, name='show_category'),

]
