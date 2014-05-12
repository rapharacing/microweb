from django.conf.urls import url
from django.conf.urls import patterns

from huddles.views import HuddleView


urlpatterns = patterns('',
    # Huddles
    url(r'^huddles/$', HuddleView.list, name='list-huddle'),
    url(r'^huddles/create/$', HuddleView.create, name='create-huddle'),
    url(r'^huddles/(?P<huddle_id>\d+)/$' , HuddleView.single, name='single-huddle'),
    url(r'^huddles/(?P<huddle_id>\d+)/leave/$', HuddleView.delete, name='delete-huddle'),
    url(r'^huddles/(?P<huddle_id>\d+)/invite/$', HuddleView.invite, name='invite-huddle'),
    url(r'^huddles/(?P<huddle_id>\d+)/newest/$', HuddleView.newest, name='newest-huddle'),
)