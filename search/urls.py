from django.conf.urls import url
from django.conf.urls import patterns

from search import views


urlpatterns = patterns('',
   url(r'^search/$', views.single, name='single-search'),
)
