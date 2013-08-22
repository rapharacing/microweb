from microcosm.api.resources import Site
from microcosm.api.resources import WhoAmI
from microcosm.api.exceptions import APIException

from requests import RequestException

import grequests
import pylibmc as memcache
import logging

from microweb import settings

logger = logging.getLogger('microcosm.middleware')

class ContextMiddleware():
    """
    Middleware for providing request context such as the current site and authentication
    status.
    """

    def __init__(self):
        self.mc = memcache.Client(['%s:%d' % (settings.MEMCACHE_HOST, settings.MEMCACHE_PORT)])

    def process_request(self, request):
        """
        Checks for access_token cookie and appends it to the request object
        if it exists.

        All requests have a view_requests attribute. This is a list of requests that must be
        executed by grequests (in parallel) to fetch data for the view.
        """

        request.access_token = None
        request.whoami_url = ''
        request.view_requests = []
        request.site = None

        if request.COOKIES.has_key('access_token'):
            request.access_token = request.COOKIES['access_token']
            url, params, headers = WhoAmI.build_request(request.META['HTTP_HOST'], request.access_token)
            request.view_requests.append(grequests.get(url, params=params, headers=headers))
            request.whoami_url = url

        site = self.mc.get(request.META['HTTP_HOST'].split('.')[0])
        if site is None:
            logger.error('Site cache miss: %s' % request.META['HTTP_HOST'].split('.')[0])
            try:
                site = Site.retrieve(request.META['HTTP_HOST'])
                self.mc.set(request.META['HTTP_HOST'].split('.')[0], site)
            except APIException, e:
                logger.error(e.message)
            except RequestException, e:
                logger.error(e.message)
        request.site = site

        return None
