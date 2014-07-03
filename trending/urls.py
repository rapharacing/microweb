from django.conf.urls import url
from django.conf.urls import patterns

from trending import views


urlpatterns = patterns('',
     url(r'^trending/$', views.list, name='list-trending'),
)
