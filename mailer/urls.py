from django.conf.urls import url
from . import views

urlpatterns =[
    url(r'^$', views.list_messages, name='list_messages'),
    url(r'^create/$', views.create_message, name='create_message')
]
