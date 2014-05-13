from django.conf.urls import url
from django.conf.urls import patterns

from microcosm.views import AuthenticationView
from microcosm.views import ErrorView
from microcosm.views import FaviconView
from microcosm.views import RobotsView
from microcosm.views import LegalView


urlpatterns = patterns('',

    # Static
    url(r'^robots\.txt$', RobotsView.as_view()),
    url(r'^favicon\.ico$', FaviconView.as_view()),

    # Auth
    url(r'^login/$', AuthenticationView.login, name='login'),
    url(r'^logout/$', AuthenticationView.logout, name='logout'),

    # Legal
    url(r'^about/$', LegalView.list, name='list-legal'),
    url(r'^about/(?P<doc_name>[a-z]+)/$', LegalView.single, name='single-legal'),

    # Echoes request headers
    url(r'^headers/', 'microcosm.views.echo_headers'),

    # Break things
    url(r'error/', ErrorView.server_error),
    url(r'notfound/', ErrorView.not_found),
    url(r'forbidden/', ErrorView.forbidden),
)
