from django.conf.urls import url
from django.conf.urls import patterns

from huddles import views


urlpatterns = patterns('',
    # Huddles
    url(r'^huddles/$', views.list, name='list-huddle'),
    url(r'^huddles/create/$', views.create, name='create-huddle'),
    url(r'^huddles/(?P<huddle_id>\d+)/$' , views.single, name='single-huddle'),
    url(r'^huddles/(?P<huddle_id>\d+)/leave/$', views.delete, name='delete-huddle'),
    url(r'^huddles/(?P<huddle_id>\d+)/invite/$', views.invite, name='invite-huddle'),
    url(r'^huddles/(?P<huddle_id>\d+)/newest/$', views.newest, name='newest-huddle'),
)