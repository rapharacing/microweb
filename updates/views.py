import requests
import grequests
import logging

from django.core.urlresolvers import reverse

from django.http import HttpResponseBadRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect

from django.shortcuts import render

from django.views.decorators.http import require_http_methods

from microcosm.api.resources import UpdateList
from microcosm.api.resources import Update
from microcosm.api.resources import UpdatePreference
from microcosm.api.resources import WatcherList
from microcosm.api.resources import Watcher
from microcosm.api.resources import Profile
from microcosm.api.resources import response_list_to_dict
from microcosm.api.resources import GlobalOptions
from microcosm.api.resources import Site

from microcosm.views import exception_handler
from microcosm.views import build_pagination_links
from microcosm.views import require_authentication

logger = logging.getLogger('updates.views')


class UpdateView(object):
    list_template = 'updates.html'

    @staticmethod
    @exception_handler
    @require_http_methods(['GET',])
    def list(request):
        # TODO: need a user friendly error page for unregistered users
        # TODO: remove 'site_section'
        if not request.access_token:
            responses = response_list_to_dict(grequests.map(request.view_requests))
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
            responses = response_list_to_dict(grequests.map(request.view_requests))
            updates_list = UpdateList(responses[url])

            view_data = {
                'user': Profile(responses[request.whoami_url], summary=False),
                'content': updates_list,
                'pagination': build_pagination_links(responses[url]['updates']['links'], updates_list.updates),
                'site_section': 'updates',
                'site': Site(responses[request.site_url]),
                }

        return render(request, UpdateView.list_template, view_data)

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['POST',])
    def mark_viewed(request, update_id):
        """
        Mark a update as viewed by setting a 'viewed' attribute.
        """

        Update.mark_viewed(request.get_host(), update_id, request.access_token)
        return HttpResponseRedirect(reverse('list-updates'))


class WatcherView(object):
    list_template = 'watchers.html'

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET', 'POST',])
    def list(request):

        if request.method == 'POST':
            if 'watcher_id' in request.POST:
                watchers = request.POST.getlist('watcher_id')
                # TODO: get rid of casts
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
            return HttpResponseRedirect(reverse('list-watchers'))

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

            return render(request, WatcherView.list_template, view_data)


    @staticmethod
    @exception_handler
    @require_http_methods(['POST',])
    def single(request):
        postdata = {
            'updateTypeId': 1,
            'itemType': request.POST.get('itemType'),
            'itemId': int(request.POST.get('itemId')),
            }
        if request.POST.get('delete'):
            Watcher.delete(request.get_host(), postdata, request.access_token)
            return HttpResponse()
        elif request.POST.get('patch'):
            postdata = {
                'itemType': request.REQUEST.get('itemType'),
                'itemId': int(request.REQUEST.get('itemId')),
                'sendEmail': "true" == request.REQUEST.get('emailMe')
            }
            response = Watcher.update(request.get_host(), postdata, request.access_token)
            if response.status_code == requests.codes.ok:
                return HttpResponse()
            else:
                return HttpResponseBadRequest()
        else:
            responsedata = Watcher.create(request.get_host(), postdata, request.access_token)
            return HttpResponse(responsedata, content_type='application/json')


class UpdatePreferenceView(object):
    list_template = 'forms/update_settings.html'

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET', 'POST',])
    def settings(request):

        if request.method == 'POST':
            for x in range(1, 10):
                if request.POST.get('id_' + str(x)):
                    postdata = {
                        'id': int(request.POST['id_' + str(x)]),
                        'sendEmail': bool(request.POST.get('send_email_' + str(x))),
                        'sendSMS': False,
                        }
                    UpdatePreference.update(
                        request.get_host(),
                        request.POST['id_' + str(x)],
                        postdata,
                        request.access_token
                    )

            postdata = {
                'sendEmail': bool(request.POST.get('profile_receive_email')),
                'sendSMS': False,
                }
            GlobalOptions.update(request.get_host(), postdata, request.access_token)
            return HttpResponseRedirect(reverse('updates-settings'))

        if request.method == 'GET':
            url, params, headers = UpdatePreference.build_request(request.get_host(), request.access_token)
            request.view_requests.append(grequests.get(url, params=params, headers=headers))

            url2, params2, headers2 = GlobalOptions.build_request(request.get_host(), request.access_token)
            request.view_requests.append(grequests.get(url2, params=params2, headers=headers2))

            responses = response_list_to_dict(grequests.map(request.view_requests))
            preference_list = UpdatePreference.from_list(responses[url])
            global_options = GlobalOptions.from_api_response(responses[url2])

            view_data = {
                'user': Profile(responses[request.whoami_url], summary=False),
                'site': Site(responses[request.site_url]),
                'content': preference_list,
                'globaloptions': global_options,
                }
            return render(request, UpdatePreferenceView.list_template, view_data)
