import pylibmc as memcache
import logging

from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.http import HttpResponseRedirect

from core.api.resources import Site
from core.api.exceptions import APIException

from requests import RequestException

logger = logging.getLogger('core.middleware.redirect')


class DomainRedirectMiddleware():
    """
    Where a site has a custom domain, the user should be permanently redirected to
    the custom domain from the microcosm subdomain.
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
                        self.mc.set(host, site, time=300)
                    except memcache.Error as e:
                        logger.error('Memcached SET error: %s' % str(e))
                except APIException, e:
                    logger.error('APIException: %s' % e.message)
                    return HttpResponseRedirect(reverse('server-error'))
                except RequestException, e:
                    logger.error('RequestException: %s' % e.message)
                    return HttpResponseRedirect(reverse('server-error'))

            # Forum owner has configured their own domain, so 301 the client.
            if hasattr(site, 'domain') and site.domain:
                # We don't support SSL on custom domains yet, so ensure the scheme is http.
                location = 'http://' + site.domain + request.get_full_path()
                logger.debug('Redirecting subdomain to: %s' % location)
                return HttpResponsePermanentRedirect(location)

        return None
