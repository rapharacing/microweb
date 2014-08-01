import logging
import grequests
import newrelic
import pylibmc as memcache

from django.conf import settings

from core.api.resources import Site
from core.api.resources import WhoAmI

logger = logging.getLogger('core.middleware.context')

class ContextMiddleware():
    """
    Provides request context such as the current site and authentication status.
    """

    def __init__(self):
        self.mc = memcache.Client(['%s:%d' % (settings.MEMCACHE_HOST, settings.MEMCACHE_PORT)])

    def process_request(self, request):
        """
        Checks for access_token cookie and appends it to the request object if present.

        All request objects have a view_requests attribute which is a list of requests
        that will be executed by grequests to fetch data for the view.
        """

        request.access_token = None
        request.whoami_url = ''
        request.view_requests = []

        if request.COOKIES.has_key('access_token'):
            request.access_token = request.COOKIES['access_token']
            request.whoami_url, params, headers = WhoAmI.build_request(request.get_host(), request.access_token)
            request.view_requests.append(grequests.get(request.whoami_url, params=params, headers=headers))
            newrelic.agent.add_custom_parameter('access_token', request.access_token[:6])

        request.site_url, params, headers = Site.build_request(request.get_host())
        request.view_requests.append(grequests.get(request.site_url, params=params, headers=headers))

