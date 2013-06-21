from django.conf.urls import patterns, include, url

from microcosm.views import ErrorView

urlpatterns = patterns(
    '',
    url(r'', include('microcosm.urls')),
)

handler403 = ErrorView.forbidden
handler404 = ErrorView.not_found
handler500 = ErrorView.server_error
