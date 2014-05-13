import requests
import grequests
import string
import datetime
import json
import logging

from functools import wraps

from django.conf import settings

from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError

from django.http import Http404
from django.http import HttpResponseNotFound
from django.http import HttpResponseForbidden
from django.http import HttpResponseServerError
from django.http import HttpResponseBadRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect

from django.shortcuts import redirect
from django.shortcuts import render

from django.template import RequestContext
from django.template import loader

from django.views.decorators.http import require_http_methods

from django.views.generic.base import RedirectView
from django.views.generic.base import TemplateView

from microcosm.api.exceptions import APIException
from microcosm.api.resources import FileMetadata
from microcosm.api.resources import MicrocosmList
from microcosm.api.resources import UpdateList
from microcosm.api.resources import Update
from microcosm.api.resources import UpdatePreference
from microcosm.api.resources import WatcherList
from microcosm.api.resources import Watcher
from microcosm.api.resources import Event
from microcosm.api.resources import Comment
from microcosm.api.resources import Conversation
from microcosm.api.resources import Profile
from microcosm.api.resources import Attachment
from microcosm.api.resources import response_list_to_dict
from microcosm.api.resources import GlobalOptions
from microcosm.api.resources import ProfileList
from microcosm.api.resources import Search
from microcosm.api.resources import Site
from microcosm.api.resources import Trending
from microcosm.api.resources import Legal

from microcosm.api.resources import build_url

from microcosm.forms.forms import ProfileEdit

logger = logging.getLogger('microcosm.views')

def exception_handler(view_func):
    """
    Decorator for view functions that raises appropriate
    errors to the user and passes data to the error view.

    Forbidden and Not Found are the only statuses that are
    communicated to the visitor. All other errors should
    be handled in client code or a generic error page will
    be displayed.
    """

    @wraps(view_func)
    def decorator(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except APIException as e:
            logger.error(str(e))
            if e.status_code == 401 or e.status_code == 403:
                raise PermissionDenied
            elif e.status_code == 404:
                raise Http404
            elif e.status_code == 400:
                # Error code 14 indicates that the requested forum does not exist.
                if e.detail['errorCode'] == 14:
                    return HttpResponseRedirect('http://microco.sm')
            else:
                raise
    return decorator


def require_authentication(view_func):
    """
    Returns HTTP 401 if request.access_token is not present.
    """

    @wraps(view_func)
    def decorator(request, *args, **kwargs):
        if hasattr(request, 'access_token'):
            return view_func(request, *args, **kwargs)
        else:
            # TODO: this should redirect to a page where the user can log in.
            raise PermissionDenied
    return decorator

def build_pagination_links(request, paged_list):
    """
    This takes the data sent in the 'links' part of an api response
    and generates a dictionary of navigation links based on that.
    """

    # trips if paged_list is not paginatedList object.
    try:
        paged_list.page
    except AttributeError:
        return {}

    page_nav = {
    'page': int(paged_list.page),
    'total_pages': int(paged_list.total_pages),
    'limit': int(paged_list.limit),
    'offset': int(paged_list.offset)
    }

    for item in request:
        item['href'] = str.replace(str(item['href']), '/api/v1', '')
        page_nav[item['rel']] = item

    return page_nav

def process_attachments(request, comment):

    """
    For the provided request, check if files are to be attached or deleted
    from the provided comment. Raises a ValidationError if any files are larger
    than 5MB.
    """

    # Check if any existing comment attachments are to be deleted.
    if request.POST.get('attachments-delete'):
        attachments_delete = request.POST.get('attachments-delete').split(",")
        for fileHash in attachments_delete:
            Attachment.delete(request.get_host(), Comment.api_path_fragment, comment.id, fileHash)

    # Check if any files have been uploaded with the request.
    if request.FILES.has_key('attachments'):
        for f in request.FILES.getlist('attachments'):
            file_request = FileMetadata.from_create_form(f)
            # Maximum file size is 5MB.
            if len(file_request.file[f.name]) >= 5242880:
                raise ValidationError
            # Associate attachment with comment using attachments API.
            else:
                file_metadata = file_request.create(request.get_host(), request.access_token)
                Attachment.create(request.get_host(), file_metadata.file_hash,
                                  comment_id=comment.id, access_token=request.access_token, file_name=f.name)





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


class TrendingView(object):
    list_template = 'trending.html'

    @staticmethod
    @exception_handler
    @require_http_methods(['GET',])
    def list(request):
        url, params, headers = Trending.build_request(request.get_host(), access_token=request.access_token)
        request.view_requests.append(grequests.get(url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))
        trending = Trending.from_api_response(responses[url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': trending,
            'pagination': build_pagination_links(responses[url]['items']['links'], trending.items),
            'site_section': 'trending'
        }

        return render(request, TrendingView.list_template, view_data)


class LegalView(object):
    list_template = 'legals.html'
    single_template = 'legal.html'

    @staticmethod
    @exception_handler
    @require_http_methods(['GET',])
    def list(request):
        responses = response_list_to_dict(grequests.map(request.view_requests))

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'site_section': 'legal'
        }

        return render(request, LegalView.list_template, view_data)


    @staticmethod
    @exception_handler
    @require_http_methods(['GET',])
    def single(request, doc_name):
        if not doc_name in ['cookies', 'privacy', 'terms']:
            return HttpResponseNotFound()

        url, params, headers = Legal.build_request(request.get_host(), doc=doc_name)
        request.view_requests.append(grequests.get(url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))

        legal = Legal.from_api_response(responses[url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': legal,
            'site_section': 'legal',
            'page_section': doc_name
        }

        return render(request, LegalView.single_template, view_data)


class ModerationView(object):
    @staticmethod
    @require_authentication
    @require_http_methods(['GET', 'POST',])
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
                    conversation = Conversation.retrieve(request.get_host(),
                        request.POST.get('item_id'), access_token=request.access_token)
                    conversation.microcosm_id = int(request.POST.get('microcosm_id'))
                    conversation.meta = {'editReason': 'Moderator moved item'}
                    conversation.update(request.get_host(), request.access_token)

            elif request.POST.get('action') == 'delete':
                if request.POST.get('item_type') == 'conversation':
                    url, params, headers = Conversation.build_request(request.get_host(),
                        request.POST.get('item_id'), access_token=request.access_token)
                if request.POST.get('item_type') == 'event':
                    url, params, headers = Event.build_request(request.get_host(), request.POST.get('item_id'),
                        access_token=request.access_token)
                payload = json.dumps([{'op': 'replace', 'path': '/meta/flags/deleted', 'value': True}])
                headers['Content-Type'] = 'application/json'
                requests.patch(url, payload, headers=headers)

            return HttpResponseRedirect(reverse('single-microcosm', args=(request.POST.get('microcosm_id'),)))

        if request.method == 'GET':
            if request.GET.get('item_type') == 'conversation':
                url, params, headers = Conversation.build_request(request.get_host(),
                    request.GET.get('item_id'), access_token=request.access_token)
                request.view_requests.append(grequests.get(url, params=params, headers=headers))
                responses = response_list_to_dict(grequests.map(request.view_requests))
                content = Conversation.from_api_response(responses[url])

            elif request.GET.get('item_type') == 'event':
                url, params, headers = Event.build_request(request.get_host(),
                    request.GET.get('item_id'), access_token=request.access_token)
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
                # Fetch list of microcosms
                view_data['microcosms'] = MicrocosmList.retrieve(request.get_host(),
                    access_token=request.access_token)

            return render(request, 'forms/moderation_item.html', view_data)



class ErrorView(object):
    @staticmethod
    def not_found(request):
        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
        }
        context = RequestContext(request, view_data)
        return HttpResponseNotFound(loader.get_template('404.html').render(context))

    @staticmethod
    def forbidden(request):
        view_data = {}

        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
            if request.whoami_url:
                view_data['user'] = Profile(responses[request.whoami_url], summary=False)
            view_data['site'] = Site(responses[request.site_url])
        except APIException as e:
            # HTTP 401 indicates a not valid access token was supplied.
            # TODO: use API detailed error codes to provide a useful message.
            if e.status_code == 401 or e.status_code == 403:
                # Template uses this in error message.
                view_data['logout'] = True
                # Try to fetch site data without access token as it may not have succeeded above.
                if not view_data.has_key('site'):
                    view_data['site'] = Site.retrieve(request.get_host())

        context = RequestContext(request, view_data)
        response = HttpResponseForbidden(loader.get_template('403.html').render(context))
        return response

    @staticmethod
    def server_error(request):
        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
        }
        context = RequestContext(request, view_data)
        return HttpResponseServerError(loader.get_template('500.html').render(context))


class AuthenticationView(object):
    @staticmethod
    @exception_handler
    def login(request):
        """
        Log a user in. Creates an access_token using a persona
        assertion and the client secret. Sets this access token as a cookie.
        'target_url' based as a GET parameter determines where the user is
        redirected.
        """

        target_url = request.POST.get('target_url')
        assertion = request.POST.get('Assertion')

        data = dict(Assertion=assertion, ClientSecret=settings.CLIENT_SECRET)

        url = build_url(request.get_host(), ['auth'])
        response = requests.post(url, data=data, headers={})
        access_token = response.json()['data']

        response = HttpResponseRedirect(target_url if target_url != '' else '/')
        expires = datetime.datetime.fromtimestamp(2 ** 31 - 1)
        response.set_cookie('access_token', access_token, expires=expires, httponly=True)
        return response

    @staticmethod
    @exception_handler
    @require_http_methods(["POST"])
    def logout(request):
        """
        Log a user out. Issues a DELETE request to the backend for the
        user's access_token, and issues a delete cookie header in response to
        clear the user's access_token cookie.
        """

        response = redirect('/')
        if request.COOKIES.has_key('access_token'):
            response.delete_cookie('access_token')
            url = build_url(request.get_host(), ['auth', request.access_token])
            requests.post(url, params={'method': 'DELETE', 'access_token': request.access_token})

        return response

def echo_headers(request):
    view_data = '<html><body><table>'
    for key in request.META.keys():
        view_data += '<tr><td>%s</td><td>%s</td></tr>' % (key, request.META[key])
    view_data += '</table></body></html>'
    return HttpResponse(view_data, content_type='text/html')


class FaviconView(RedirectView):
    def get_redirect_url(self, **kwargs):
        return settings.STATIC_URL + 'img/favico.png'


class RobotsView(TemplateView):
    template_name = 'robots.txt'
    content_type = 'text/plain'

    def get_context_data(self, **kwargs):
        return super(RobotsView, self).get_context_data(**kwargs)
