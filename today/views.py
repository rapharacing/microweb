import grequests
import logging

from django.shortcuts import render

from django.views.decorators.http import require_http_methods

from core.api.resources import api_url_to_gui_url
from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import Search
from core.api.resources import Site

from core.api.exceptions import APIException

from core.views import respond_with_error

logger = logging.getLogger('today.views')
single_template = 'today.html'


@require_http_methods(['GET',])
def single(request):

    searchParams = request.GET.dict()
    searchParams['type'] = ['conversation','event','profile','huddle']
    searchParams['since'] = 1

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
        'site_section': 'today'
    }

    if responses[url].get('results'):
        view_data['pagination'] = build_pagination_links(
                    responses[url]['results']['links'],
                    search.results
                )

    return render(request, single_template, view_data)

def build_pagination_links(request, paged_list):
    """
    This takes the data sent in the 'links' part of an api response
    and generates a dictionary of navigation links based on that.
    """

    if not hasattr(paged_list, 'page'):
        return {}

    page_nav = {
    'page': int(paged_list.page),
    'total_pages': int(paged_list.total_pages),
    'limit': int(paged_list.limit),
    'offset': int(paged_list.offset)
    }

    for item in request:
        url = str.replace(str(item['href']), '/search', '/today')
        url = str.replace(url, '?since=1&type=conversation&type=event&type=profile&type=huddle', '')
        url = str.replace(url, '&since=1&type=conversation&type=event&type=profile&type=huddle', '')
        item['href'] = api_url_to_gui_url(url)
        page_nav[item['rel']] = item

    return page_nav