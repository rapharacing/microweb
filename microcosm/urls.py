from django.conf.urls import url
from django.conf.urls import patterns

from microcosm.views import MicrocosmView
from microcosm.views import EventView
from microcosm.views import ConversationView
from microcosm.views import CommentView
from microcosm.views import ProfileView
from microcosm.views import AuthenticationView
from microcosm.views import GeoView


urlpatterns = patterns('',

    # Static
    url(r'^robots\.txt$', 'django.views.generic.simple.direct_to_template', {'template': 'robots.txt', 'mimetype': 'text/plain'}),
    url(r'^favicon\.ico$', 'django.views.generic.simple.redirect_to', {'url': '/static/img/favico.png'}),

    # Auth
    url(r'^login/$', AuthenticationView.login, name='login'),
    url(r'^logout/$', AuthenticationView.logout, name='logout'),

    # Microcosms
    url(r'^$', MicrocosmView.list),
    url(r'^microcosms/$', MicrocosmView.list, name='list-microcosms'),
    url(r'^microcosms/create/$', MicrocosmView.create, name='create-microcosm'),
    url(r'^microcosms/(?P<microcosm_id>\d+)/$', MicrocosmView.single, name='single-microcosm'),
    url(r'^microcosms/(?P<microcosm_id>\d+)/edit/$', MicrocosmView.edit, name='edit-microcosm'),
    url(r'^microcosms/(?P<microcosm_id>\d+)/delete/$', MicrocosmView.delete, name='delete-microcosm'),

    # Interstitial page for creating an item (Event, ...) within a microcosm.
    url(r'^microcosms/(?P<microcosm_id>\d+)/create/$', MicrocosmView.create_item_choice, name='item-choice'),

    # Events
    url(r'^microcosms/(?P<microcosm_id>\d+)/create/event/$', EventView.create, name='create-event'),
    url(r'^events/(?P<event_id>\d+)/$', EventView.single, name='single-event'),
    url(r'^events/(?P<event_id>\d+)/edit/$', EventView.edit, name='edit-event'),
    url(r'^events/(?P<event_id>\d+)/delete/$', EventView.delete, name='delete-event'),
    # RSVP to an event
    url(r'^events/(?P<event_id>\d+)/rsvp/$', EventView.rsvp, name='rsvp-event'),

    # Conversations
    url(r'^microcosms/(?P<microcosm_id>\d+)/create/conversation/$', ConversationView.create, name='create-conversation'),
    url(r'^conversations/(?P<conversation_id>\d+)/$' , ConversationView.single, name='single-conversation'),
    url(r'^conversations/(?P<conversation_id>\d+)/edit/$', ConversationView.edit, name='edit-conversation'),
    url(r'^conversations/(?P<conversation_id>\d+)/delete/$', ConversationView.delete, name='delete-conversation'),

    # Comments
    url(r'comments/create/$', CommentView.create, name='create-comment'),
    url(r'comments/(?P<comment_id>\d+)/$', CommentView.single, name='single-comment'),
    url(r'comments/(?P<comment_id>\d+)/edit/$', CommentView.edit, name='edit-comment'),
    url(r'comments/(?P<comment_id>\d+)/delete/$', CommentView.delete, name='delete-comment'),

    # User profiles
    url(r'^profiles/(?P<profile_id>\d+)/$', ProfileView.single, name='single-profile'),
    url(r'^profiles/(?P<profile_id>\d+)/edit/$', ProfileView.edit, name='edit-profile'),

    # Proxy geocoding requests to the backend
    url(r'^geocode/$', GeoView.geocode, name='geocode'),

    # Echoes request headers
    url(r'^headers/', 'microcosm.views.echo_headers'),
)
