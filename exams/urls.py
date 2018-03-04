from django.conf.urls import url
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from . import views

urlpatterns =[
    url(r'^$', views.list_meta_categories, name='list_meta_categories'),
    url(r'^ajax/general/correct_percentage$', views.get_correct_percentage, name='get_correct_percentage'),
    url(r'^ajax/general/count_answers$', views.count_answers, name='count_answers'),
    url(r'^ajax/general/questions$', views.QuestionAutocomplete.as_view(), name='autocomplete_questions'),
    url(r'^ajax/collectors/approve_revision/(?P<pk>\d+)$', views.mark_revision_approved, name='mark_revision_approved'),
    url(r'^ajax/collectors/assign_questions$', views.assign_questions, name='assign_questions'),
    url(r'^ajax/collectors/delete_explanation_revision/(?P<pk>\d+)$', views.delete_explanation_revision, name='delete_explanation_revision'),
    url(r'^ajax/collectors/delete_question/(?P<pk>\d+)$', views.delete_question, name='delete_question'),
    url(r'^ajax/collectors/delete_revision/(?P<pk>\d+)$', views.delete_revision, name='delete_revision'),
    url(r'^ajax/collectors/handle_duplicate$', views.handle_duplicate, name='handle_duplicate'),
    url(r'^ajax/collectors/handle_question/(?P<exam_pk>\d+)(?:/(?P<question_pk>\d+))?$', views.handle_question, name='handle_question'),
    url(r'^ajax/collectors/pend_revision/(?P<pk>\d+)$', views.mark_revision_pending, name='mark_revision_pending'),
    url(r'^ajax/collectors/show_explanation_revision/(?P<pk>\d+)$', views.show_explanation_revision, name='show_explanation_revision'),
    url(r'^ajax/collectors/show_question/(?P<pk>\d+)(?:/(?P<revision_pk>\d+))?$', views.show_question, name='show_question'),
    url(r'^ajax/collectors/show_revision_comparison/(?P<pk>\d+)/(?P<review>review)?$', views.show_revision_comparison,name='show_revision_comparison'),
    url(r'^ajax/collectors/update_stats/(?P<pk>\d+)$', views.update_exam_stats, name='update_exam_stats'),
    url(r'^ajax/examinees/(?P<pk>\d+)/credits$', views.show_credits, name='show_credits'),
    url(r'^ajax/examinees/correct_answer$', views.correct_answer, name='correct_answer'),
    url(r'^ajax/examinees/count_selection/(?P<exam_pk>\d+)$', views.get_selected_question_count, name='get_selected_question_count'),
    url(r'^ajax/examinees/delete_correction$', views.delete_correction, name='delete_correction'),
    url(r'^ajax/examinees/delete_session$', views.delete_session, name='delete_session'),
    url(r'^ajax/examinees/edit$', views.contribute_revision, name='contribute_revision'),
    url(r'^ajax/examinees/explain$', views.contribute_explanation, name='contribute_explanation'),
    url(r'^ajax/examinees/mnemonics$', views.contribute_mnemonics, name='contribute_mnemonics'),
    url(r'^ajax/examinees/submit_answer$', views.submit_answer, name='submit_answer'),
    url(r'^ajax/examinees/submit_highlight$', views.submit_highlight, name='submit_highlight'),
    url(r'^ajax/examinees/toggle_marked$', views.toggle_marked, name='toggle_marked'),
    url(r'^tmep/end_session/$', TemplateView.as_view(template_name='exams/session_end.html'), name="session_end"),
    url(r'^previous/$', views.list_previous_sessions, name='list_previous_sessions'),

    url(r'^performance/$', views.show_my_performance, name='show_my_performance'),
    url(r'^performance/(?P<exam_pk>\d+)/$', views.show_my_performance_per_exam, name='show_my_performance_per_exam'),

    url(r'^search/$', views.search, name='search'),
    url(r'^assigned/$', views.list_assigned_questions, name='list_assigned_questions'),

    # Indicators were moved to the core app
    url(r'^indicators/$', RedirectView.as_view(pattern_name='show_indicator_index')),
    url(r'^indicators/teams/$', RedirectView.as_view(pattern_name='show_indicator_index')),
    url(r'^indicators/teams/(?P<team_pk>\d+)/$', RedirectView.as_view(pattern_name='show_team_indicators')),
    url(r'^indicators/categories/$', RedirectView.as_view(pattern_name='show_indicator_index')),
    url(r'^indicators/categories/(?P<slugs>[/\d\w\-]+)/$', RedirectView.as_view(pattern_name='show_indicator_index')),

    url(r'^contributions/(?:(?P<user_pk>\d+)/)?$',views.list_contributions, name='list_contributions'),

    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/(?P<pk>\d+)/control/approve$', views.approve_question, name='approve_question'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/add/$', views.add_question, name='add_question'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/list/$', views.list_questions, name='list_questions'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/list/duplicate/$', views.list_duplicates, name='list_duplicates'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<pk>\d+)/control/list/(?P<selector>[\-\d\w_]+)/$', views.list_questions, name='list_questions_by_selector'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/questions/(?P<pk>\d+)/$', views.list_revisions, name='list_revisions'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/questions/(?P<pk>\d+)/edit/$', views.submit_revision,name='submit_revision'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/question/(?P<question_pk>\d+)/$', views.show_question, name='show_question'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/session/(?P<session_pk>\d+)/(?:(?P<question_pk>\d+)/)?$', views.show_session, name='show_session'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/session/partial_questions$', views.list_partial_session_questions, name='list_partial_session_questions'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/session/(?P<session_pk>\d+)/results/$', views.show_session_results, name='show_session_results'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/contributions/$',views.approve_user_contributions, name='approve_user_contributions'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/$', views.create_session, name='create_session'),
    url(r'^(?P<slugs>[/\d\w\-]+)/(?P<exam_pk>\d+)/automatic$', views.create_session_automatically, name='create_session_automatically'),

    # has to be the very last
    url(r'^(?P<slugs>[/\d\w\-]+)/$', views.show_category, name='show_category'),
]
