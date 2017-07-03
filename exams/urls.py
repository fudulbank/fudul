from django.conf.urls import url, include
from exams import views

urlpatterns =[
    url(r'^$', views.list_meta_categories, name='list_meta_categories'),
    url(r'^ajax/questions$', views.QuestionAutocomplete.as_view(), name='autocomplete_questions'),
    url(r'^ajax/show_question/(?P<pk>\d+)(?:/(?P<revision_pk>\d+))?$', views.show_question, name='show_question'),
    url(r'^ajax/handle_question/(?P<exam_pk>\d+)$', views.handle_question, name='handle_question'),
    url(r'^ajax/delete_question/(?P<pk>\d+)$', views.delete_question, name='delete_question'),
    url(r'^ajax/handle_session/(?P<exam_pk>\d+)$', views.handle_session, name='handle_session'),
    url(r'^ajax/start_session/(?P<session_pk>\d+)$', views.start_session_ajax, name='start_session_ajax'),
    url(r'^ajax/check_answer/$', views.check_answer, name='check_answer'),

    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/add/$', views.add_question, name='add_question'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/list/$', views.list_questions, name='list_questions'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/questions/(?P<pk>\d+)/$', views.list_revisions, name='list_revisions'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/questions/(?P<pk>\d+)/edit/$', views.submit_revision,name='submit_revision'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/questions/status/list/$', views.list_question_per_status,name='list_question_per_status'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/session/$', views.create_session, name='create_session'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/session/(?P<session_pk>\d+)/$', views.session, name='session'),

    url(r'^(?P<slugs>[/\d\w\-]+)/$', views.show_category, name='show_category'),
]
