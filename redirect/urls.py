from django.conf.urls import url
from django.conf.urls import patterns

from redirect import views

urlpatterns = patterns('',
    url(r'.+/$', views.redirect_or_404),
)
