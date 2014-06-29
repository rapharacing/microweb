from django.conf.urls import url
from django.conf.urls import patterns

from profiles.views import ProfileView

urlpatterns = patterns('',
    url(r'^profiles/$', ProfileView.list, name='list-profiles'),
    url(r'^profiles/(?P<profile_id>\d+)/$', ProfileView.single, name='single-profile'),
    url(r'^profiles/(?P<profile_id>\d+)/edit/$', ProfileView.edit, name='edit-profile'),
    url(r'^profiles/read/$', ProfileView.mark_read, name='mark-read'),
)
