import grequests
import logging

from django.shortcuts import render

from django.views.decorators.http import require_http_methods

from core.api.resources import Profile

from core.api.resources import response_list_to_dict
from core.api.resources import Search
from core.api.resources import Site

from core.views import exception_handler
from core.views import build_pagination_links

logger = logging.getLogger('search.views')


class SearchView(object):
    single_template = 'search.html'

    @staticmethod
    @exception_handler
    @require_http_methods(['GET',])
    def single(request):

        # pagination offset
        offset = int(request.GET.get('offset', 0))
        q = request.GET.get('q')

        url, params, headers = Search.build_request(request.get_host(), params=request.GET.dict(),
                                                    access_token=request.access_token)
        request.view_requests.append(grequests.get(url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))
        search = Search.from_api_response(responses[url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': search,
            }

        if responses[url].get('results'):
            view_data['pagination'] = build_pagination_links(responses[url]['results']['links'], search.results)

        return render(request, SearchView.single_template, view_data)

