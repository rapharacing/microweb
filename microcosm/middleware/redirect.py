import pylibmc as memcache
import logging

from django.http import HttpResponsePermanentRedirect

from microweb import settings

from microcosm.api.resources import Site
from microcosm.api.exceptions import APIException

from requests import RequestException

logger = logging.getLogger('microcosm.middleware')


class DomainRedirectMiddleware():
    """
    Where a site has a custom domain, the user should be permanently redirected to
    the custom domain from the microcosm subdomain.

    TODO: expiry header on the redirect response, once an approach to site cache
    invalidation has been decided.
    """

    def __init__(self):
        self.mc = memcache.Client(['%s:%d' % (settings.MEMCACHE_HOST, settings.MEMCACHE_PORT)])

    def process_request(self, request):

        host = request.get_host()

        # Only look at requests to example.microco.sm
        if host.endswith(settings.API_DOMAIN_NAME):

            # Fetch site from cache
            try:
                site = self.mc.get(host)
            except memcache.Error as e:
                logger.error('Memcached GET error: %s' % str(e))
                site = None

            # Not in cache or retrieval failed
            if site is None:
                try:
                    site = Site.retrieve(host)
                    try:
                        self.mc.set(host, site)
                    except memcache.Error as e:
                        logger.error('Memcached SET error: %s' % str(e))
                except APIException, e:
                    logger.error(e.message)
                except RequestException, e:
                    logger.error(e.message)

            # Site has a custom domain, so redirect
            if site and site.domain != '':
                # Prepend URL scheme to custom domain
                location = 'https://' if request.is_secure() else 'http://' + site.domain

                # Append query string to new location, if it exists
                query_string = request.META.get('QUERY_STRING', None)
                if query_string:
                    location += '?' + query_string

                logger.debug('Redirecting subdomain to: %s' % location)
                return HttpResponsePermanentRedirect(location)

        return None
