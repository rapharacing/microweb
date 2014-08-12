from django.conf.urls import url
from django.conf.urls import patterns

from today import views

urlpatterns = patterns('',
     url(r'^today/$', views.single, name='single-today'),
)
