from django.conf.urls import url, include
from exams import views
from django.views.generic import TemplateView

urlpatterns =[
    url(r'^$', views.list_meta_categories, name='list_meta_categories'),
    url(r'^ajax/general/questions$', views.QuestionAutocomplete.as_view(), name='autocomplete_questions'),
    url(r'^ajax/general/subjects', views.SubjectQuestionCount.as_view(), name='subject_questions_count'),
    url(r'^ajax/general/exam_types', views.ExamTypeQuestionCount.as_view(), name='exam_type_questions_count'),
    url(r'^ajax/collectors/show_question/(?P<pk>\d+)(?:/(?P<revision_pk>\d+))?$', views.show_question, name='show_question'),
    url(r'^ajax/collectors/handle_question/(?P<exam_pk>\d+)(?:/(?P<question_pk>\d+))?$', views.handle_question, name='handle_question'),
    url(r'^ajax/collectors/delete_question/(?P<pk>\d+)$', views.delete_question, name='delete_question'),
    url(r'^ajax/collectors/delete_revision/(?P<pk>\d+)$', views.delete_revision, name='delete_revision'),
    url(r'^ajax/collectors/approve_revision/(?P<pk>\d+)$', views.mark_revision_approved, name='mark_revision_approved'),
    url(r'^ajax/collectors/pend_revision/(?P<pk>\d+)$', views.mark_revision_pending, name='mark_revision_pending'),
    url(r'^ajax/collectors/show_revision_comparison/(?P<pk>\d+)(?:/(?P<revision_pk>\d+))?$', views.show_revision_comparison,name='show_revision_comparison'),
    url(r'^ajax/examiners/submit_answer$', views.submit_answer, name='submit_answer'),
    url(r'^ajax/examiners/toggle_marked$', views.toggle_marked, name='toggle_marked'),
    url(r'^ajax/examiners/list$', views.list_session_questions, name='list_session_questions'),
    url(r'^ajax/examiners/explain$', views.contribute_explanation, name='contribute_explanation'),
    url(r'^ajax/examiners/edit$', views.contribute_revision, name='contribute_revision'),
    url(r'^ajax/examiners/(?P<pk>\d+)/credits$', views.show_credits, name='show_credits'),
    url(r'^tmep/end_session/$', TemplateView.as_view(template_name='exams/session_end.html'), name="session_end"),
    url(r'^previous_sessions/$', views.show_pevious_sessions, name='show_previous_sessions'),


    url(r'^indicators/categories/$', views.list_meta_categories, {'indicators': True}, name='list_category_indicators'),
    url(r'^indicators/categories/(?P<slugs>[/\d\w\-]+)/$', views.show_category, {'indicators': True}, name='show_category_indicators'),

    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/(?P<pk>\d+)/control/approve$', views.approve_question, name='approve_question'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/add/$', views.add_question, name='add_question'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/list/$', views.list_questions, name='list_questions'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/questions/(?P<pk>\d+)/$', views.list_revisions, name='list_revisions'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/questions/(?P<pk>\d+)/edit/$', views.submit_revision,name='submit_revision'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/questions/status/list/$', views.list_question_per_status,name='list_question_per_status'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/session/$', views.create_session, name='create_session'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/session/(?P<session_pk>\d+)/(?:(?P<question_pk>\d+)/)?$', views.show_session, name='show_session'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/session/(?P<session_pk>\d+)/results/$', views.show_session_results, name='show_session_results'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/contributions/$',views.approve_user_contributions, name='approve_user_contributions'),

    url(r'^(?P<slugs>[/\d\w\-]+)/$', views.show_category, name='show_category'),
]
