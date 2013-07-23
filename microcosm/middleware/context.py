from microcosm.api.resources import Site
from microcosm.api.resources import WhoAmI
from microcosm.api.exceptions import APIException

import requests
from requests import RequestException


import logging
from microweb.helpers import build_url

logger = logging.getLogger('microcosm.middleware')

class ContextMiddleware():
    """
    Middleware for providing request context such as the current site and
    who the user is (through the whoami API call).
    """

    def process_request(self, request):
        """
        Checks for access_token cookie and appends it to the request object
        if it exists. If the access token is invalid, flags it for deletion.

        Populates request.whoami with the result of the whoami API call.
        """

        request.access_token = None
        request.delete_token = False
        request.whoami = None
        request.site = None
        request.create_profile = False

        if request.COOKIES.has_key('access_token'):
            request.access_token = request.COOKIES['access_token']

            # if a bad access token is provided, flag for deletion
            try:
                request.whoami = WhoAmI.retrieve(request.META['HTTP_HOST'], request.access_token)
            except APIException, e:
                if e.status_code == 401:
                    request.delete_token = True

        try:
            request.site = Site.retrieve(request.META['HTTP_HOST'])
        except APIException, e:
            logger.error(e.message)
        except RequestException, e:
            logger.error(e.message)

        return None


    def process_response(self, request, response):
        """
        Deletes the user's access token cookie if it has previously
        been marked as invalid (by process_request)
        """

        if hasattr(request, 'delete_token') and request.delete_token:
            response.delete_cookie('access_token')
            requests.delete(build_url(request.META['HTTP_HOST'], ['auth', request.COOKIES['access_token']]))
        return response