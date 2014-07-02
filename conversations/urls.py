from django.conf.urls import url
from django.conf.urls import patterns

from conversations import views

urlpatterns = patterns('',
    url(r'^microcosms/(?P<microcosm_id>\d+)/create/conversation/$', views.create, name='create-conversation'),
    url(r'^conversations/(?P<conversation_id>\d+)/$' , views.single, name='single-conversation'),
    url(r'^conversations/(?P<conversation_id>\d+)/edit/$', views.edit, name='edit-conversation'),
    url(r'^conversations/(?P<conversation_id>\d+)/delete/$', views.delete, name='delete-conversation'),
    url(r'^conversations/(?P<conversation_id>\d+)/newest/$', views.newest, name='newest-conversation'),
)
