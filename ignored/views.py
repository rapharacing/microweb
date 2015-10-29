import requests
import grequests
import logging

from django.core.urlresolvers import reverse

from django.http import HttpResponseBadRequest
from django.http import HttpResponseRedirect

from django.shortcuts import render

from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_safe

from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import Ignored
from core.api.resources import Site

from core.api.exceptions import APIException

from core.views import build_pagination_links
from core.views import respond_with_error
from core.views import require_authentication

logger = logging.getLogger('ignored.views')

template_name = 'ignored.html'


@require_authentication
@require_safe
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
        grequests.get(url, params=params, headers=headers)
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
        'pagination': build_pagination_links(responses[url]['ignored']['links'], ignoredItems),
        'site_section': 'ignored',
    }

    return render(request, template_name, view_data)


@require_authentication
@require_http_methods(['POST',])
@cache_control(must_revalidate=True, max_age=0)
def ignore(request):
    """
    View for (un)ignoring a single item.
    """
    item_type = request.POST.get('item_type')
    item_id = int(request.POST.get('item_id'))
    delete = False
    if request.POST.get('delete'):
        delete = True

    if item_type == '':
        return HttpResponseBadRequest()

    if item_id <= 0:
        return HttpResponseBadRequest()

    data = {'itemType': item_type, 'itemId': item_id}

    if delete:
        response = Ignored.delete_api(
            request.get_host(),
            data,
            request.access_token
        )
    else:
        response = Ignored.add_api(
            request.get_host(),
            data,
            request.access_token
        )

    if response.status_code != requests.codes.ok:
        print 'ignore: ' + response.text
        return HttpResponseBadRequest()

    return HttpResponseRedirect(reverse('list-ignored'))
