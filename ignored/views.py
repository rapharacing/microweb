import grequests
import logging

from django.shortcuts import render

from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods


from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import Ignored
from core.api.resources import Site

from core.api.exceptions import APIException

from core.views import build_pagination_links
from core.views import respond_with_error

logger = logging.getLogger('ignored.views')

template_name = 'ignored.html'


@require_http_methods(['GET'])
@cache_control(must_revalidate=True, max_age=0)
def ignored(request):

    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    url, params, headers = Ignored.build_request(
        request.get_host(),
        offset=offset,
        access_token=request.access_token
    )
    request.view_requests.append(
        grequests.get(url, params=params, headers=headers, timeout=5)
    )

    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    ignoredItems = Ignored.from_api_response(responses[url])


    view_data = {
        'user': Profile(
            responses[request.whoami_url], summary=False
        ) if request.whoami_url else None,
        'site': Site(responses[request.site_url]),
        'content': ignoredItems,
        'site_section': 'ignored',
    }

    if responses[url].get('items'):
        view_data.pagination = build_pagination_links(responses[url]['items']['links'], ignoredItems.items)

    return render(request, template_name, view_data)
