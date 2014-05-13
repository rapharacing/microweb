from django.conf.urls import url
from django.conf.urls import patterns

from search.views import SearchView


urlpatterns = patterns('',
   # Search
   url(r'^search/$', SearchView.single, name='single-search'),
)
