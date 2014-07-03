import grequests
import logging

from django.shortcuts import render

from django.views.decorators.http import require_http_methods

from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import Site
from core.api.resources import Trending

from core.api.exceptions import APIException

from core.views import respond_with_error
from core.views import build_pagination_links

logger = logging.getLogger('trending.views')
list_template = 'trending.html'


@require_http_methods(['GET',])
def list(request):
    url, params, headers = Trending.build_request(request.get_host(), access_token=request.access_token)
    request.view_requests.append(grequests.get(url, params=params, headers=headers))
    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    trending = Trending.from_api_response(responses[url])

    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
        'site': Site(responses[request.site_url]),
        'content': trending,
        'pagination': build_pagination_links(responses[url]['items']['links'], trending.items),
        'site_section': 'trending'
    }

    return render(request, list_template, view_data)


