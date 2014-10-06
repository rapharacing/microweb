from django.conf.urls import url
from django.conf.urls import patterns

from ignored import views

urlpatterns = patterns('',
     url(r'^ignored/$',  views.ignored, name='list-ignored'),
     url(r'^ignore/$',   views.ignore,  name='ignore-item'),
     url(r'^unignore/$', views.ignore,  name='unignore-item'),
)
