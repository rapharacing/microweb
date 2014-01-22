import pylibmc as memcache
import logging

from django.http import HttpResponsePermanentRedirect
from django.conf import settings

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
                # No custom domains can be SSL, so we must be redirecting to the
                # http version regardless of how they came into the site
                location = 'http://' + site.domain + request.get_full_path()

                logger.debug('Redirecting subdomain to: %s' % location)
                
                return HttpResponsePermanentRedirect(location)

        return None
