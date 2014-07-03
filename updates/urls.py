from django.conf.urls import url
from django.conf.urls import patterns

from updates import views


urlpatterns = patterns('',
    # Updates
    url(r'^updates/$', views.list_updates, name='list-updates'),
    url(r'^updates/settings/$', views.settings, name='updates-settings'),

    # Watchers
    url(r'^watchers/$', views.watchers, name='watchers'),
)
