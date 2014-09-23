from django.conf.urls import url
from django.conf.urls import patterns

from ignored import views

urlpatterns = patterns('',
     url(r'^ignored/$', views.ignored, name='list-ignored'),
)
