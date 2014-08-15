import requests
import grequests
import json

from django.core.urlresolvers import reverse

from django.http import HttpResponseRedirect

from django.shortcuts import render

from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods

from core.api.resources import MicrocosmList
from core.api.resources import Event
from core.api.resources import Conversation
from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import Site

from core.views import require_authentication

@require_authentication
@require_http_methods(['GET', 'POST',])
@cache_control(must_revalidate=True, max_age=0)
def item(request):
    """
    View for moderation actions on a single item.
    """

    if request.method == 'POST':
        if request.POST.get('action') == 'move':
            if request.POST.get('item_type') == 'event':
                event = Event.retrieve(request.get_host(), request.POST.get('item_id'),
                    access_token=request.access_token)
                event.microcosm_id = int(request.POST.get('microcosm_id'))
                event.meta = {'editReason': 'Moderator moved item'}
                event.update(request.get_host(), request.access_token)
            elif request.POST.get('item_type') == 'conversation':
                conversation = Conversation.retrieve(request.get_host(), request.POST.get('item_id'),
                    access_token=request.access_token)
                conversation.microcosm_id = int(request.POST.get('microcosm_id'))
                conversation.meta = {'editReason': 'Moderator moved item'}
                conversation.update(request.get_host(), request.access_token)

        else:
            # These are all PATCH requests and we need the item in question first
            if request.POST.get('item_type') == 'conversation':
                url, params, headers = Conversation.build_request(request.get_host(), request.POST.get('item_id'),
                    access_token=request.access_token)
            if request.POST.get('item_type') == 'event':
                url, params, headers = Event.build_request(request.get_host(), request.POST.get('item_id'),
                    access_token=request.access_token)

            # And then to execute the PATCH against the item
            if request.POST.get('action') == 'delete':
                payload = json.dumps([{'op': 'replace', 'path': '/meta/flags/deleted', 'value': True}])
                headers['Content-Type'] = 'application/json'
                requests.patch(url, payload, headers=headers)

            elif request.POST.get('action') == 'undelete':
                payload = json.dumps([{'op': 'replace', 'path': '/meta/flags/deleted', 'value': False}])
                headers['Content-Type'] = 'application/json'
                requests.patch(url, payload, headers=headers)

            elif request.POST.get('action') == 'approve':
                payload = json.dumps([{'op': 'replace', 'path': '/meta/flags/moderated', 'value': False}])
                headers['Content-Type'] = 'application/json'
                requests.patch(url, payload, headers=headers)

            elif request.POST.get('action') == 'pin':
                payload = json.dumps([{'op': 'replace', 'path': '/meta/flags/sticky', 'value': True}])
                headers['Content-Type'] = 'application/json'
                requests.patch(url, payload, headers=headers)

            elif request.POST.get('action') == 'unpin':
                payload = json.dumps([{'op': 'replace', 'path': '/meta/flags/sticky', 'value': False}])
                headers['Content-Type'] = 'application/json'
                requests.patch(url, payload, headers=headers)

            elif request.POST.get('action') == 'open':
                payload = json.dumps([{'op': 'replace', 'path': '/meta/flags/open', 'value': True}])
                headers['Content-Type'] = 'application/json'
                requests.patch(url, payload, headers=headers)

            elif request.POST.get('action') == 'close':
                payload = json.dumps([{'op': 'replace', 'path': '/meta/flags/open', 'value': False}])
                headers['Content-Type'] = 'application/json'
                requests.patch(url, payload, headers=headers)

        return HttpResponseRedirect(reverse('single-microcosm', args=(request.POST.get('microcosm_id'),)))

    if request.method == 'GET':
        if request.GET.get('item_type') == 'conversation':
            url, params, headers = Conversation.build_request(request.get_host(), request.GET.get('item_id'),
                access_token=request.access_token)
            request.view_requests.append(grequests.get(url, params=params, headers=headers))
            responses = response_list_to_dict(grequests.map(request.view_requests))
            content = Conversation.from_api_response(responses[url])

        elif request.GET.get('item_type') == 'event':
            url, params, headers = Event.build_request(request.get_host(), request.GET.get('item_id'),
                access_token=request.access_token)
            request.view_requests.append(grequests.get(url, params=params, headers=headers))
            responses = response_list_to_dict(grequests.map(request.view_requests))
            content = Event.from_api_response(responses[url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'site': Site(responses[request.site_url]),
            'content': content,
            'item_type': request.GET.get('item_type'),
            'action': request.GET.get('action'),
        }

        if request.GET.get('action') == 'move':
            # Fetch list of microcosms to supply in form.
            view_data['microcosms'] = MicrocosmList.retrieve(request.get_host(), access_token=request.access_token)

        return render(request, 'forms/moderation_item.html', view_data)