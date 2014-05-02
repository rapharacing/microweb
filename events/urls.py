from django.conf.urls import url
from django.conf.urls import patterns

from events.views import EventView
from events.views import GeoView

urlpatterns = patterns('',
    # Events
    url(r'^microcosms/(?P<microcosm_id>\d+)/create/event/$', EventView.create, name='create-event'),
    url(r'^events/(?P<event_id>\d+)/$', EventView.single, name='single-event'),
    url(r'^events/(?P<event_id>\d+)/edit/$', EventView.edit, name='edit-event'),
    url(r'^events/(?P<event_id>\d+)/delete/$', EventView.delete, name='delete-event'),
    url(r'^events/(?P<event_id>\d+)/newest/$', EventView.newest, name='newest-event'),
    # RSVP to an event
    url(r'^events/(?P<event_id>\d+)/rsvp/$', EventView.rsvp, name='rsvp-event'),

    # Proxy geocoding requests to the backend
    url(r'^geocode/$', GeoView.geocode, name='geocode'),
)