from django.conf.urls import url, include
from blocks import views

urlpatterns =[
#    url(r'^$', views.list_institutions, name='list'),
    url(r'^colleges/(?P<pk>\d+)/$', views.list_colleges, name='list_colleges'),
    url(r'^years/(?P<pk>\d+)/$', views.list_years, name='list_years'),
    url(r'^blocks/(?P<pk>\d+)/$', views.list_blocks, name='list_blocks'),
    url(r'^blocks/add/(?P<year_pk>\d+)/$', views.handle_block, name='handle_block'),
    url(r'^subjects/(?P<pk>\d+)/$', views.list_subjects, name='list_subjects'),
    url(r'^subjects/(?P<subject_pk>\d+)/question/$', views.handle_question, name='handle_question'),
    url(r'^questions/(?P<pk>\d+)/$', views.list_questions, name='list_questions'),
    url(r'^questionform/$', views.add_question, name='add_questions'),

]
