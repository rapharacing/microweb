import grequests
import logging

from django.shortcuts import render

from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods

from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import Search
from core.api.resources import Site

from core.api.exceptions import APIException

from core.views import respond_with_error
from core.views import build_pagination_links

logger = logging.getLogger('search.views')
single_template = 'search.html'


@require_http_methods(['GET',])
@cache_control(must_revalidate=True, max_age=0)
def single(request):

    searchParams = request.GET.dict()
    if searchParams.get('defaults'):
        searchParams['inTitle'] = 'true'
        searchParams['sort'] = 'date'

    url, params, headers = Search.build_request(request.get_host(), params=searchParams,
        access_token=request.access_token)
    request.view_requests.append(grequests.get(url, params=params, headers=headers))

    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    search = Search.from_api_response(responses[url])

    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
        'site': Site(responses[request.site_url]),
        'content': search,
    }

    if responses[url].get('results'):
        view_data['pagination'] = build_pagination_links(responses[url]['results']['links'], search.results)

    return render(request, single_template, view_data)

