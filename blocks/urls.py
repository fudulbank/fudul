from django.conf.urls import url, include
from blocks import views

urlpatterns =[
    url(r'^viewexam/(?P<pk>\d+)/$', views.add_question, name='add_question'),
    url(r'^$', views.list_meta_categories, name='list_meta_categories'),
    url(r'category/(?P<slugs>[/\d\w\-]+)$',views.show_category, name='show_category'),
    url(r'^blocks/add/(?P<year_pk>\d+)/$', views.handle_block, name='handle_block'),
    url(r'^subjects/(?P<subject_pk>\d+)/question/$', views.handle_question, name='handle_question'),
    url(r'^questions/(?P<pk>\d+)/$', views.list_questions, name='list_questions'),
    url(r'^questionform/$', views.add_question, name='add_questions'),

]
