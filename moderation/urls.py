from django.conf.urls import url
from django.conf.urls import patterns

from moderation.views import ModerationView


urlpatterns = patterns('',
    url(r'^moderate/$', ModerationView.item, name='moderate-item'),
)
