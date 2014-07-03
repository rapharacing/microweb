from django.conf.urls import url
from django.conf.urls import patterns

from moderation import views


urlpatterns = patterns('',
    url(r'^moderate/$', views.item, name='moderate-item'),
)
