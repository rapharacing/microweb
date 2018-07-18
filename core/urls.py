from django.conf.urls import url
from django.conf.urls import patterns

from core.views import AuthenticationView
from core.views import Auth0View
from core.views import ErrorView
from core.views import FaviconView
from core.views import RobotsView
from core.views import LegalView


urlpatterns = patterns('',

    # Static
    url(r'^robots\.txt$', RobotsView.as_view()),
    url(r'^favicon\.ico$', FaviconView.as_view()),

    # Auth
    url(r'^login/$', AuthenticationView.login, name='login'),
    url(r'^auth0login/$', Auth0View.login, name='auth0login'),
    url(r'^logout/$', AuthenticationView.logout, name='logout'),

    # Legal
    url(r'^about/$', LegalView.list, name='list-legal'),
    url(r'^about/(?P<doc_name>[a-z]+)/$', LegalView.single, name='single-legal'),

    # Echoes request headers
    url(r'^headers/', 'core.views.echo_headers'),

    # Break things
    url(r'error/', ErrorView.server_error),
    url(r'notfound/', ErrorView.not_found),
    url(r'forbidden/', ErrorView.forbidden),
)
