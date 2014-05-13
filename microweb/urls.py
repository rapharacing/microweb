from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from microcosm.views import ErrorView

from microweb import settings


urlpatterns = patterns(
    '',
	url(r'', include('microcosms.urls')),
    url(r'', include('microcosm.urls')),
    url(r'', include('conversations.urls')),
    url(r'', include('events.urls')),
    url(r'', include('huddles.urls')),
    url(r'', include('comments.urls')),
    url(r'', include('profiles.urls')),
    url(r'', include('updates.urls')),
    url(r'', include('search.urls')),
    url(r'', include('trending.urls')),
)

# Serve static files with gunicorn if DEBUG is true.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

handler403 = ErrorView.forbidden
handler404 = ErrorView.not_found
handler500 = ErrorView.server_error
