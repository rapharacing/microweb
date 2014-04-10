from django.conf.urls import url
from django.conf.urls import patterns

from microcosm.views import MicrocosmView
from microcosm.views import MembershipView
from microcosm.views import EventView
from microcosm.views import ConversationView
from microcosm.views import UpdateView
from microcosm.views import WatcherView
from microcosm.views import UpdatePreferenceView
from microcosm.views import CommentView
from microcosm.views import ProfileView
from microcosm.views import AuthenticationView
from microcosm.views import ErrorView
from microcosm.views import GeoView
from microcosm.views import FaviconView
from microcosm.views import RobotsView
from microcosm.views import SearchView
from microcosm.views import HuddleView
from microcosm.views import TrendingView
from microcosm.views import LegalView
from microcosm.views import ModerationView


urlpatterns = patterns('',

	# Static
	url(r'^robots\.txt$', RobotsView.as_view()),
	url(r'^favicon\.ico$', FaviconView.as_view()),

	# Auth
	url(r'^login/$', AuthenticationView.login, name='login'),
	url(r'^logout/$', AuthenticationView.logout, name='logout'),

	# Microcosms
	url(r'^$', MicrocosmView.list, name='index'),
	url(r'^microcosms/$', MicrocosmView.list, name='list-microcosms'),
	url(r'^microcosms/create/$', MicrocosmView.create, name='create-microcosm'),
	url(r'^microcosms/(?P<microcosm_id>\d+)/$', MicrocosmView.single, name='single-microcosm'),
	url(r'^microcosms/(?P<microcosm_id>\d+)/edit/$', MicrocosmView.edit, name='edit-microcosm'),
	url(r'^microcosms/(?P<microcosm_id>\d+)/delete/$', MicrocosmView.delete, name='delete-microcosm'),

	url(r'^microcosms/(?P<microcosm_id>\d+)/memberships/$', MembershipView.list, name="list-memberships"),
	url(r'^microcosms/(?P<microcosm_id>\d+)/memberships/create/$', MembershipView.create, name="create-memberships"),

	# Events
	url(r'^microcosms/(?P<microcosm_id>\d+)/create/event/$', EventView.create, name='create-event'),
	url(r'^events/(?P<event_id>\d+)/$', EventView.single, name='single-event'),
	url(r'^events/(?P<event_id>\d+)/edit/$', EventView.edit, name='edit-event'),
	url(r'^events/(?P<event_id>\d+)/delete/$', EventView.delete, name='delete-event'),
	url(r'^events/(?P<event_id>\d+)/newest/$', EventView.newest, name='newest-event'),
	# RSVP to an event
	url(r'^events/(?P<event_id>\d+)/rsvp/$', EventView.rsvp, name='rsvp-event'),

	# Conversations
	url(r'^microcosms/(?P<microcosm_id>\d+)/create/conversation/$', ConversationView.create, name='create-conversation'),
	url(r'^conversations/(?P<conversation_id>\d+)/$' , ConversationView.single, name='single-conversation'),
	url(r'^conversations/(?P<conversation_id>\d+)/edit/$', ConversationView.edit, name='edit-conversation'),
	url(r'^conversations/(?P<conversation_id>\d+)/delete/$', ConversationView.delete, name='delete-conversation'),
	url(r'^conversations/(?P<conversation_id>\d+)/newest/$', ConversationView.newest, name='newest-conversation'),

	# Comments
	url(r'comments/create/$', CommentView.create, name='create-comment'),
	url(r'comments/(?P<comment_id>\d+)/$', CommentView.single, name='single-comment'),
	url(r'comments/(?P<comment_id>\d+)/edit/$', CommentView.edit, name='edit-comment'),
	url(r'comments/(?P<comment_id>\d+)/delete/$', CommentView.delete, name='delete-comment'),
	url(r'comments/(?P<comment_id>\d+)/incontext/$', CommentView.incontext, name='incontext-comment'),
	url(r'comments/(?P<comment_id>\d+)/source/$', CommentView.source, name='source-comment'),
	url(r'comments/(?P<comment_id>\d+)/attachments/$', CommentView.attachments, name='attachment-comment'),

	# Huddles
	url(r'^huddles/$', HuddleView.list, name='list-huddle'),
	url(r'^huddles/create/$', HuddleView.create, name='create-huddle'),
	url(r'^huddles/(?P<huddle_id>\d+)/$' , HuddleView.single, name='single-huddle'),
	url(r'^huddles/(?P<huddle_id>\d+)/leave/$', HuddleView.delete, name='delete-huddle'),
	url(r'^huddles/(?P<huddle_id>\d+)/invite/$', HuddleView.invite, name='invite-huddle'),
	url(r'^huddles/(?P<huddle_id>\d+)/newest/$', HuddleView.newest, name='newest-huddle'),

	# Updates
	url(r'^updates/$', UpdateView.list, name='list-updates'),
	url(r'^updates/settings/$', UpdatePreferenceView.settings, name='updates-settings'),

	# Watchers
	url(r'^watchers/$', WatcherView.single, name='single-watcher'),

	# User profiles
	url(r'^profiles/$', ProfileView.list, name='list-profiles'),
	url(r'^profiles/(?P<profile_id>\d+)/$', ProfileView.single, name='single-profile'),
	url(r'^profiles/(?P<profile_id>\d+)/edit/$', ProfileView.edit, name='edit-profile'),

	# Search
	url(r'^search/$', SearchView.single, name='single-search'),

	# Trending
	url(r'^trending/$', TrendingView.list, name='list-trending'),

	# Legal
	url(r'^about/$', LegalView.list, name='list-legal'),
	url(r'^about/(?P<doc_name>[a-z]+)/$', LegalView.single, name='single-legal'),

	# Moderation
	url(r'^moderate/$', ModerationView.item, name='moderate-item'),

	# Proxy geocoding requests to the backend
	url(r'^geocode/$', GeoView.geocode, name='geocode'),

	# Echoes request headers
	url(r'^headers/', 'microcosm.views.echo_headers'),

	# Break things
	url(r'error/', ErrorView.server_error),
	url(r'notfound/', ErrorView.not_found),
	url(r'forbidden/', ErrorView.forbidden),
)
