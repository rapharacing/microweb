import logging

from django.conf import settings

import requests
import grequests
import pylibmc as memcache

from microcosm.api.resources import Site
from microcosm.api.resources import WhoAmI
from microcosm.api.exceptions import APIException

logger = logging.getLogger('microcosm.middleware')

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
        request.site = None

        if request.COOKIES.has_key('access_token'):
            request.access_token = request.COOKIES['access_token']
            url, params, headers = WhoAmI.build_request(request.get_host(), request.access_token)
            request.view_requests.append(grequests.get(url, params=params, headers=headers))
            request.whoami_url = url

        try:
            site = self.mc.get(request.get_host())
        except memcache.Error as e:
            logger.error('Memcached error: %s' % str(e))
            site = None

        if site is None:
            try:
                site = Site.retrieve(request.get_host())
                try:
                    # Cached for 5 minutes to spare useless requests but still
                    # provide a useful indication in the stats of how many people
                    # are online now
                    self.mc.set(request.get_host(), site, time=5*60)
                except memcache.Error as e:
                    logger.error('Memcached error: %s' % str(e))
            except APIException, e:
                logger.error(e.message)
            except requests.RequestException, e:
                logger.error(e.message)
        request.site = site

        return None
