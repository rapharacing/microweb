import grequests
import logging

from django.core.urlresolvers import reverse

from django.http import HttpResponseRedirect

from django.shortcuts import render

from django.views.decorators.http import require_http_methods

from core.api.resources import UpdateList
from core.api.resources import UpdatePreference
from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import GlobalOptions
from core.api.resources import Site
from core.api.resources import Watcher
from core.api.resources import WatcherList

from core.api.exceptions import APIException

from core.views import respond_with_error
from core.views import build_pagination_links
from core.views import require_authentication


logger = logging.getLogger('updates.views')
list_template = 'updates.html'
settings_template = 'forms/update_settings.html'
watchers_template = 'watchers.html'


@require_http_methods(['GET',])
def list_updates(request):

    if not request.access_token:
        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException as exc:
            return respond_with_error(request, exc)
        view_data = {
            'user': False,
            'site_section': 'updates',
            'site': Site(responses[request.site_url]),
        }
    else:
        # pagination offset
        offset = int(request.GET.get('offset', 0))

        url, params, headers = UpdateList.build_request(request.get_host(), offset=offset,
            access_token=request.access_token)
        request.view_requests.append(grequests.get(url, params=params, headers=headers))
        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException as exc:
            return respond_with_error(request, exc)
        updates_list = UpdateList(responses[url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'content': updates_list,
            'pagination': build_pagination_links(responses[url]['updates']['links'], updates_list.updates),
            'site_section': 'updates',
            'site': Site(responses[request.site_url]),
        }

    return render(request, list_template, view_data)


@require_authentication
@require_http_methods(['GET', 'POST',])
def settings(request):

    if request.method == 'POST':

        # Update global settings for notifications.
        postdata = {
            'sendEmail': bool(request.POST.get('profile_receive_email')),
            'sendSMS': False,
        }
        try:
            GlobalOptions.update(request.get_host(), postdata, request.access_token)
        except APIException as exc:
            return respond_with_error(request, exc)

        # Update settings for each notification type.
        for x in range(1, 10):
            if request.POST.get('id_' + str(x)):
                postdata = {
                    'id': int(request.POST['id_' + str(x)]),
                    'sendEmail': bool(request.POST.get('send_email_' + str(x))),
                    'sendSMS': False,
                    }
                try:
                    UpdatePreference.update(request.get_host(), request.POST['id_' + str(x)],
                        postdata, request.access_token)
                except APIException as exc:
                    return respond_with_error(request, exc)

        return HttpResponseRedirect(reverse('updates-settings'))

    if request.method == 'GET':
        url, params, headers = UpdatePreference.build_request(request.get_host(), request.access_token)
        request.view_requests.append(grequests.get(url, params=params, headers=headers))

        url2, params2, headers2 = GlobalOptions.build_request(request.get_host(), request.access_token)
        request.view_requests.append(grequests.get(url2, params=params2, headers=headers2))

        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException as exc:
            return respond_with_error(request, exc)

        preference_list = UpdatePreference.from_list(responses[url])
        global_options = GlobalOptions.from_api_response(responses[url2])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'site': Site(responses[request.site_url]),
            'content': preference_list,
            'globaloptions': global_options,
        }
        return render(request, settings_template, view_data)


@require_authentication
@require_http_methods(['GET', 'POST',])
def watchers(request):

    if request.method == 'POST':
        if 'watcher_id' in request.POST:
            watchers = request.POST.getlist('watcher_id')
            for w in watchers:
                if request.POST.get('delete_watcher_' + str(w)):
                    Watcher.delete(request.get_host(), w, request.access_token)
                else:
                    postdata = {
                        'id': int(w),
                        'sendEmail': bool(request.POST.get('send_email_' + str(w))),
                        'receiveSMS': False,
                        }
                    Watcher.update(request.get_host(), int(w), postdata, request.access_token)
        return HttpResponseRedirect(reverse('watchers'))

    if request.method == 'GET':
        # pagination offset
        offset = int(request.GET.get('offset', 0))

        url, params, headers = WatcherList.build_request(request.get_host(), offset=offset,
                                                         access_token=request.access_token)
        request.view_requests.append(grequests.get(url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))
        watchers_list = WatcherList(responses[url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'site': Site(responses[request.site_url]),
            'content': watchers_list,
            'pagination': build_pagination_links(responses[url]['watchers']['links'], watchers_list.watchers)
        }

        return render(request, watchers_template, view_data)