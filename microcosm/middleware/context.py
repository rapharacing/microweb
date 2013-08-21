from microcosm.api.resources import Site
from microcosm.api.resources import WhoAmI
from microcosm.api.exceptions import APIException

from requests import RequestException

import grequests
import memcache
import logging

from microweb import settings

logger = logging.getLogger('microcosm.middleware')

class ContextMiddleware():
    """
    Middleware for providing request context such as the current site and
    who the user is (through the whoami API call).
    """
    def __init__(self):
        self.mc = memcache.Client(['%s:%d' % (settings.MEMCACHE_HOST, settings.MEMCACHE_PORT)] , debug=0)

    def process_request(self, request):
        """
        Checks for access_token cookie and appends it to the request object
        if it exists. If the access token is invalid, flags it for deletion.

        Populates request.whoami with the result of the whoami API call.
        """

        request.access_token = None
        request.site = None

        if request.COOKIES.has_key('access_token'):
            request.access_token = request.COOKIES['access_token']
            url, params, headers = WhoAmI.build_request(request.META['HTTP_HOST'], request.access_token)
            request.whoami_req = grequests.get(url, params=params, headers=headers)

        site = self.mc.get(request.META['HTTP_HOST'])
        if not site:
            logger.error('Site cache miss: %s' % request.META['HTTP_HOST'])
            try:
                site = Site.retrieve(request.META['HTTP_HOST'])
                self.mc.set(request.META['HTTP_HOST'], site, time=3600)
            except APIException, e:
                logger.error(e.message)
            except RequestException, e:
                logger.error(e.message)
        request.site = site

        return None
