from django.conf.urls import url
from django.conf.urls import patterns

from moderation import views


urlpatterns = patterns('',
    url(r'^moderate/$', views.confirm, name='moderate-item'),
    url(r'^moderate/do/$', views.moderate, name='actually-moderate-item'),
)
