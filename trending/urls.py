from django.conf.urls import url
from django.conf.urls import patterns

from trending.views import TrendingView


urlpatterns = patterns('',
     url(r'^trending/$', TrendingView.list, name='list-trending'),
)
