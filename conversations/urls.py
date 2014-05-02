from django.conf.urls import url
from django.conf.urls import patterns

from conversations.views import ConversationView

urlpatterns = patterns('',
    url(r'^microcosms/(?P<microcosm_id>\d+)/create/conversation/$', ConversationView.create, name='create-conversation'),
    url(r'^conversations/(?P<conversation_id>\d+)/$' , ConversationView.single, name='single-conversation'),
    url(r'^conversations/(?P<conversation_id>\d+)/edit/$', ConversationView.edit, name='edit-conversation'),
    url(r'^conversations/(?P<conversation_id>\d+)/delete/$', ConversationView.delete, name='delete-conversation'),
    url(r'^conversations/(?P<conversation_id>\d+)/newest/$', ConversationView.newest, name='newest-conversation'),
)
