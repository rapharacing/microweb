import requests
import grequests

from functools import wraps
from microweb import settings
from microweb.settings import PAGE_SIZE
from microweb.helpers import join_path_fragments
from microweb.helpers import build_url
from urllib import urlencode
from urlparse import parse_qs
from urlparse import urlparse
from urlparse import urlunparse

from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import HttpResponseNotFound
from django.http import HttpResponseForbidden
from django.http import HttpResponseServerError
from django.http import HttpResponseBadRequest
from django.http import HttpResponse
from django.http import HttpResponseNotAllowed
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import RequestContext
from django.template import loader

from django.views.generic.base import RedirectView
from django.views.generic.base import TemplateView

from microcosm.api.exceptions import APIException
from microcosm.api.resources import FileMetadata
from microcosm.api.resources import Microcosm
from microcosm.api.resources import MicrocosmList
from microcosm.api.resources import AlertList
from microcosm.api.resources import Alert
from microcosm.api.resources import AlertPreference
from microcosm.api.resources import WatcherList
from microcosm.api.resources import Watcher
from microcosm.api.resources import GeoCode
from microcosm.api.resources import Event
from microcosm.api.resources import AttendeeList
from microcosm.api.resources import Comment
from microcosm.api.resources import Conversation
from microcosm.api.resources import Profile
from microcosm.api.resources import Attachment
from microcosm.api.resources import RESOURCE_PLURAL
from microcosm.api.resources import COMMENTABLE_ITEM_TYPES
from microcosm.api.resources import response_list_to_dict
from microcosm.api.resources import GlobalOptions

from microcosm.forms.forms import EventCreate
from microcosm.forms.forms import EventEdit
from microcosm.forms.forms import MicrocosmCreate
from microcosm.forms.forms import MicrocosmEdit
from microcosm.forms.forms import ConversationCreate
from microcosm.forms.forms import ConversationEdit
from microcosm.forms.forms import CommentForm
from microcosm.forms.forms import ProfileEdit


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
            if e.status_code == 401 or e.status_code == 403:
                raise PermissionDenied
            elif e.status_code == 404:
                raise Http404
            else:
                raise

    return decorator


def build_pagination_links(request, paged_list):
    """
    Builds page navigation links based on the request path
    and links supplied in a paginated list.
    """

    page_nav = {}

    if paged_list.links.get('first'):
        page_nav['first'] = request.path

    if paged_list.links.get('prev'):
        offset = paged_list.offset
        page_nav['prev'] = urlunparse(('', '', request.path, '', 'offset=%d' % (offset - PAGE_SIZE), '',))

    if paged_list.links.get('next'):
        offset = paged_list.offset
        page_nav['next'] = urlunparse(('', '', request.path, '', 'offset=%d' % (offset + PAGE_SIZE), '',))

    if paged_list.links.get('last'):
        offset = paged_list.max_offset
        page_nav['last'] = urlunparse(('', '', request.path, '', 'offset=%d' % offset, '',))

    return page_nav


class ConversationView(object):

    create_form = ConversationCreate
    edit_form = ConversationEdit
    form_template = 'forms/conversation.html'
    single_template = 'conversation.html'

    @staticmethod
    @exception_handler
    def single(request, conversation_id):
        if request.method == 'GET':
            # Offset for paging of event comments
            offset = int(request.GET.get('offset', 0))

            conversation_url, params, headers = Conversation.build_request(
                request.META['HTTP_HOST'],
                id=conversation_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(grequests.get(conversation_url, params=params, headers=headers))
            responses = response_list_to_dict(grequests.map(request.view_requests))
            conversation = Conversation.from_api_response(responses[conversation_url])
            comment_form = CommentForm(initial=dict(itemId=conversation_id, itemType='conversation'))

            view_data = {
                'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
                'site': request.site,
                'content': conversation,
                'comment_form': comment_form,
                'pagination': build_pagination_links(request, conversation.comments),
                'item_type': 'conversation'
            }

            return render(request, ConversationView.single_template, view_data)
        elif request.method == 'POST':
            postdata = {
                'alertTypeId': int(request.POST.get('alert_type_id')),
                'itemTypeId': 6,
                'itemId': int(conversation_id),
            }
            Watcher.create(
                request.META['HTTP_HOST'],
                postdata,
                request.access_token
            )
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    @staticmethod
    @exception_handler
    def create(request, microcosm_id):
        """
        Create a conversation.
        """

        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

        if request.method == 'POST':
            form = ConversationView.create_form(request.POST)
            if form.is_valid():
                conv_request = Conversation.from_create_form(form.cleaned_data)
                conv_response = conv_request.create(request.META['HTTP_HOST'], request.access_token)
                return HttpResponseRedirect(reverse('single-conversation', args=(conv_response.id,)))
            else:
                view_data['form'] = form
                return render(request, ConversationView.form_template, view_data)

        elif request.method == 'GET':
            view_data['form'] = ConversationView.create_form(initial=dict(microcosmId=microcosm_id))
            return render(request, ConversationView.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])

    @staticmethod
    @exception_handler
    def edit(request, conversation_id):
        """
        Edit a conversation.
        """

        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

        if request.method == 'POST':
            form = ConversationView.edit_form(request.POST)

            if form.is_valid():
                conv_request = Conversation.from_edit_form(form.cleaned_data)
                conv_response = conv_request.update(request.META['HTTP_HOST'], request.access_token)
                return HttpResponseRedirect(reverse('single-conversation', args=(conv_response.id,)))
            else:
                view_data['form'] = form
                return render(request, ConversationView.form_template, view_data)

        elif request.method == 'GET':
            conversation = Conversation.retrieve(
                request.META['HTTP_HOST'],
                id=conversation_id,
                access_token=request.access_token
            )
            view_data['form'] = ConversationView.edit_form.from_conversation_instance(conversation)
            return render(request, ConversationView.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])

    @staticmethod
    @exception_handler
    def delete(request, conversation_id):
        """
        Delete a conversation and be redirected to the parent microcosm.
        """

        if request.method == 'POST':
            conversation = Conversation.retrieve(
                request.META['HTTP_HOST'],
                conversation_id,
                access_token=request.access_token
            )
            conversation.delete(request.META['HTTP_HOST'], request.access_token)
            return HttpResponseRedirect(reverse('single-microcosm', args=(conversation.microcosm_id,)))
        else:
            return HttpResponseNotAllowed()

    @staticmethod
    @exception_handler
    def newest(request, conversation_id):
        """
        Get redirected to the first unread post in a conversation
        """
        if request.method == 'GET':
            response = Conversation.newest(
                request.META['HTTP_HOST'],
                conversation_id,
                access_token=request.access_token
            )
            #because redirects are always followed, we can't just get the 'location' value
            response = response['comments']['links']
            for link in response:
                if link['rel'] == 'self':
                    response = link['href']
            response = str.replace(str(response),'/api/v1','')
            pr = urlparse(response)
            queries = parse_qs(pr[4])
            frag = ""
            if queries.get('comment_id'):
                frag = 'comment' + queries['comment_id'][0]
                del queries['comment_id']
            # queries is a dictionary of 1-item lists (as we don't re-use keys in our query string)
            # urlencode will encode the lists into the url (offset=[25]) etc.  So get the values straight.
            for (key, value) in queries.items():
                queries[key] = value[0]
            queries = urlencode(queries)
            response = urlunparse((pr[0],pr[1],pr[2],pr[3],queries,frag))
            return HttpResponseRedirect(response)
        else:
            return HttpResponseNotAllowed()

class ProfileView(object):

    edit_form = ProfileEdit
    form_template = 'forms/profile.html'
    single_template = 'profile.html'

    @staticmethod
    @exception_handler
    def single(request, profile_id):
        """
        Display a single profile by ID.
        """

        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': request.site
        }

        profile = Profile.retrieve(
            request.META['HTTP_HOST'],
            profile_id,
            request.access_token
        )

        view_data['content'] = profile

        return render(request, ProfileView.single_template, view_data)

    @staticmethod
    @exception_handler
    def edit(request, profile_id):
        """
        Edit a user profile (profile name or avatar).
        """

        responses = response_list_to_dict(grequests.map(request.view_requests))
        user = Profile(responses[request.whoami_url], summary=False)
        view_data = dict(user=user, site=request.site)

        if request.method == 'POST':
            form = ProfileView.edit_form(request.POST)
            if form.is_valid():
                if request.FILES.has_key('avatar'):
                    file_request = FileMetadata.from_create_form(request.FILES['avatar'])
                    # File must be under 30KB
                    # TODO: use Django's built-in field validators and error messaging
                    if len(file_request.file['files']) >= 30720:
                        view_data['form'] = form
                        view_data['avatar_error'] = 'Sorry, the file you upload must be under 30KB and square.'
                        return render(request, ProfileView.form_template, view_data)
                    else:
                        file_metadata = file_request.create(request.META['HTTP_HOST'], request.access_token)
                        Attachment.create(
                            request.META['HTTP_HOST'],
                            file_metadata.file_hash,
                            profile_id=user.id,
                            access_token=request.access_token
                        )
                profile_request = Profile(form.cleaned_data)
                profile_response = profile_request.update(request.META['HTTP_HOST'], request.access_token)
                return HttpResponseRedirect(reverse('single-profile', args=(profile_response.id,)))
            else:
                view_data['form'] = form
                return render(request, ProfileView.form_template, view_data)

        elif request.method == 'GET':
            user_profile = Profile.retrieve(
                request.META['HTTP_HOST'],
                profile_id,
                request.access_token
            )
            view_data['form'] = ProfileView.edit_form(user_profile.as_dict)
            return render(request, ProfileView.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])


class MicrocosmView(object):

    create_form = MicrocosmCreate
    edit_form = MicrocosmEdit
    form_template = 'forms/microcosm.html'
    single_template = 'microcosm.html'
    list_template = 'microcosms.html'

    @staticmethod
    @exception_handler
    def single(request, microcosm_id):
        if request.method == 'GET':
            # record offset for paging of items within the microcosm
            offset = int(request.GET.get('offset', 0))

            microcosm_url, params, headers = Microcosm.build_request(
                request.META['HTTP_HOST'],
                id=microcosm_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(grequests.get(microcosm_url, params=params, headers=headers))
            responses = response_list_to_dict(grequests.map(request.view_requests))
            microcosm = Microcosm.from_api_response(responses[microcosm_url])

            view_data = {
                'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
                'site': request.site,
                'content': microcosm,
                'pagination': build_pagination_links(request, microcosm.items)
            }

            return render(request, MicrocosmView.single_template, view_data)

        elif request.method == 'POST':
            postdata = {
                'alertTypeId': int(request.POST.get('alert_type_id')),
                'itemTypeId': 2,
                'itemId': int(microcosm_id),
            }
            Watcher.create(
                request.META['HTTP_HOST'],
                postdata,
                request.access_token
            )
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


    @staticmethod
    @exception_handler
    def list(request):

        # record offset for paging of microcosms
        offset = int(request.GET.get('offset', 0))

        microcosms_url, params, headers = MicrocosmList.build_request(
            request.META['HTTP_HOST'],
            offset=offset,
            access_token=request.access_token
        )

        request.view_requests.append(grequests.get(microcosms_url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))

        microcosms = MicrocosmList(responses[microcosms_url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': request.site,
            'content': microcosms,
            'pagination': build_pagination_links(request, microcosms.microcosms)
        }

        return render(request, MicrocosmView.list_template, view_data)

    @staticmethod
    @exception_handler
    def create(request):

        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

        if request.method == 'POST':
            form = MicrocosmView.create_form(request.POST)
            if form.is_valid():
                microcosm_request = Microcosm.from_create_form(form.cleaned_data)
                microcosm_response = microcosm_request.create(request.META['HTTP_HOST'], request.access_token)
                return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm_response.id,)))
            else:
                view_data['form'] = form
                return render(request, MicrocosmView.form_template, view_data)

        elif request.method == 'GET':
            view_data['form'] = MicrocosmView.create_form()
            return render(request, MicrocosmView.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])

    @staticmethod
    @exception_handler
    def edit(request, microcosm_id):

        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

        if request.method == 'POST':
            form = MicrocosmView.edit_form(request.POST)
            if form.is_valid():
                microcosm_request = Microcosm.from_edit_form(form.cleaned_data)
                microcosm_response = microcosm_request.update(request.META['HTTP_HOST'], request.access_token)
                return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm_response.id,)))
            else:
                view_data['form'] = form
                return render(request, MicrocosmView.form_template, view_data)

        elif request.method == 'GET':
            microcosm = Microcosm.retrieve(
                request.META['HTTP_HOST'],
                id=microcosm_id,
                access_token=request.access_token
            )
            view_data['form'] = MicrocosmView.edit_form(microcosm.as_dict)
            return render(request, MicrocosmView.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])

    @staticmethod
    @exception_handler
    def delete(request, microcosm_id):
        if request.method == 'POST':
            microcosm = Microcosm.retrieve(request.META['HTTP_HOST'], microcosm_id, access_token=request.access_token)
            microcosm.delete(request.META['HTTP_HOST'], request.access_token)
            return HttpResponseRedirect(reverse(MicrocosmView.list))
        return HttpResponseNotAllowed(['POST'])

    @staticmethod
    @exception_handler
    def create_item_choice(request, microcosm_id):
        """
        Interstitial page for creating an item (e.g. Event) belonging to a microcosm.
        """

        microcosm_url, params, headers = Microcosm.build_request(
            request.META['HTTP_HOST'],
            microcosm_id,
            access_token=request.access_token
        )
        request.view_requests.append(grequests.get(microcosm_url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))

        view_data = {
            'user' : Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site' : request.site,
            'content' : Microcosm.from_api_response(responses[microcosm_url])
        }

        return render(request, 'create_item_choice.html', view_data)


class EventView(object):

    create_form = EventCreate
    edit_form = EventEdit
    form_template = 'forms/event.html'
    single_template = 'event.html'
    comment_form = CommentForm

    @staticmethod
    @exception_handler
    def single(request, event_id):
        """
        Display a single event with comments and attendees.
        """
        if request.method == 'GET':
            # Offset for paging of event comments
            offset = int(request.GET.get('offset', 0))

            event_url, event_params, event_headers = Event.build_request(
                request.META['HTTP_HOST'],
                id=event_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(grequests.get(event_url, params=event_params, headers=event_headers))

            att_url, att_params, att_headers = Event.build_attendees_request(
                request.META['HTTP_HOST'],
                event_id,
                request.access_token
            )
            request.view_requests.append(grequests.get(att_url, params=att_params, headers=att_headers))

            responses = response_list_to_dict(grequests.map(request.view_requests))
            event = Event.from_api_response(responses[event_url])
            comment_form = CommentForm(initial=dict(itemId=event_id, itemType='event'))

            view_data = {
                'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
                'site': request.site,
                'content': event,
                'comment_form': comment_form,
                'pagination': build_pagination_links(request, event.comments),
                'item_type': 'event',
                'attendees': AttendeeList(responses[att_url])
            }

            return render(request, EventView.single_template, view_data)

        elif request.method == 'POST':
            postdata = {
                'alertTypeId': int(request.POST.get('alert_type_id')),
                'itemTypeId': 9,
                'itemId': int(event_id),
            }
            Watcher.create(
                request.META['HTTP_HOST'],
                postdata,
                request.access_token
            )
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    @staticmethod
    @exception_handler
    def create(request, microcosm_id):
        """
        Create an event within a microcosm.
        """

        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

        if request.method == 'POST':
            form = EventView.create_form(request.POST)
            if form.is_valid():
                event_request = Event.from_create_form(form.cleaned_data)
                event_response = event_request.create(request.META['HTTP_HOST'], request.access_token)
                return HttpResponseRedirect(reverse('single-event', args=(event_response.id,)))
            else:
                view_data['form'] = form
                return render(request, EventView.form_template, view_data)

        elif request.method == 'GET':
            view_data['form'] = EventView.create_form(initial=dict(microcosmId=microcosm_id))
            return render(request, EventView.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])

    @staticmethod
    @exception_handler
    def edit(request, event_id):
        """
        Edit an event.
        """

        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

        if request.method == 'POST':
            form = EventView.edit_form(request.POST)
            if form.is_valid():
                event_request = Event.from_edit_form(form.cleaned_data)
                event_response = event_request.update(request.META['HTTP_HOST'], request.access_token)
                return HttpResponseRedirect(reverse('single-event', args=(event_response.id,)))
            else:
                view_data['form'] = form
                return render(request, EventView.form_template, view_data)

        elif request.method == 'GET':
            event = Event.retrieve(request.META['HTTP_HOST'], id=event_id, access_token=request.access_token)
            view_data['form'] = EventView.edit_form.from_event_instance(event)
            return render(request, EventView.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])

    @staticmethod
    @exception_handler
    def delete(request, event_id):
        """
        Delete an event and be redirected to the parent microcosm.
        """

        if request.method == 'POST':
            event = Event.retrieve(
                request.META['HTTP_HOST'],
                event_id,
                access_token=request.access_token
            )
            event.delete(request.META['HTTP_HOST'], request.access_token)
            return HttpResponseRedirect(reverse('single-microcosm', args=(event.microcosm_id,)))
        else:
            return HttpResponseNotAllowed()

    @staticmethod
    @exception_handler
    def newest(request, event_id):
        """
        Get redirected to the first unread post in a conversation
        """
        if request.method == 'GET':
            response = Event.newest(
                request.META['HTTP_HOST'],
                event_id,
                access_token=request.access_token
            )
            #because redirects are always followed, we can't just get the 'location' value
            response = response['comments']['links']
            for link in response:
                if link['rel'] == 'self':
                    response = link['href']
            response = str.replace(str(response),'/api/v1','')
            pr = urlparse(response)
            queries = parse_qs(pr[4])
            frag = ""
            if queries.get('comment_id'):
                frag = 'comment' + queries['comment_id'][0]
                del queries['comment_id']
            # queries is a dictionary of 1-item lists (as we don't re-use keys in our query string)
            # urlencode will encode the lists into the url (offset=[25]) etc.  So get the values straight.
            for (key, value) in queries.items():
                queries[key] = value[0]
            queries = urlencode(queries)
            response = urlunparse((pr[0],pr[1],pr[2],pr[3],queries,frag))
            return HttpResponseRedirect(response)
        else:
            return HttpResponseNotAllowed()

    @staticmethod
    def rsvp(request, event_id):
        """
        Create an attendee (RSVP) for an event. An attendee can be in one of four states:
        invited, confirmed, maybe, no.
        """
        responses = response_list_to_dict(grequests.map(request.view_requests))
        user = Profile(responses[request.whoami_url], summary=False)

        if request.method == 'POST':
            if user:
                attendee = {
                    'RSVP' : request.POST['rsvp'],
                    'AttendeeId' : user.id
                }
                Event.rsvp(
                    request.META['HTTP_HOST'],
                    event_id,
                    user.id,
                    attendee,
                    access_token=request.access_token
                )
                return HttpResponseRedirect(reverse('single-event', args=(event_id,)))
            else:
                raise PermissionDenied
        else:
            raise HttpResponseNotAllowed(['POST'])


class CommentView(object):

    create_form = CommentForm
    edit_form = CommentForm
    form_template = 'forms/create_comment.html'
    single_template = 'comment.html'

    @staticmethod
    def fill_from_get(request, initial):
        """
        Populate comment form fields from GET parameters.
        """

        if request.GET.has_key('itemId'):
            initial['itemId'] = int(request.GET.get('itemId', None))

        if request.GET.has_key('itemType'):
            if request.GET['itemType'] not in COMMENTABLE_ITEM_TYPES:
                raise ValueError
            initial['itemType'] = request.GET.get('itemType', None)

        if request.GET.has_key('inReplyTo'):
            initial['inReplyTo'] = int(request.GET.get('inReplyTo', None))

        return initial

    @staticmethod
    def build_comment_location(comment):

        path = join_path_fragments([RESOURCE_PLURAL[comment.item_type], comment.item_id])

        if 'offset' in comment.meta.links.get('via'):
            offset = comment.meta.links.get('via').split('offset=')[1]
            location = urlunparse((
                '', '', path, '',
                'offset=%s' % offset,
                'comment%d' % comment.id,)
            )
        else:
            location = urlunparse((
                '', '', path, '', '',
                'comment%d' % comment.id,)
            )

        return location

    @staticmethod
    @exception_handler
    def single(request, comment_id):
        """
        Display a single comment.
        """

        url, params, headers = Comment.build_request(
            request.META['HTTP_HOST'],
            id=comment_id,
            access_token=request.access_token
        )
        request.view_requests.append(grequests.get(url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': request.site,
            'content': Comment.from_api_response(responses[url]),
        }

        return render(request, CommentView.single_template, view_data)

    @staticmethod
    @exception_handler
    def create(request):
        """
        Comment forms populate attributes from GET parameters, so require the create
        method to be extended.
        """

        if not request.access_token:
            raise PermissionDenied

        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

        if request.method == 'POST':
            form = CommentForm(request.POST)
            if form.is_valid():
                comment_request = Comment.from_create_form(form.cleaned_data)
                comment_response = comment_request.create(request.META['HTTP_HOST'], access_token=request.access_token)
                if comment_response.meta.links.get('via'):
                    return HttpResponseRedirect(CommentView.build_comment_location(comment_response))
                else:
                    return HttpResponseRedirect(reverse('single-comment', args=(comment_response.id,)))
            else:
                view_data['form'] = form
                return render(request, CommentView.form_template, view_data)

        elif request.method == 'GET':
            initial = CommentView.fill_from_get(request, {})
            view_data['form'] = CommentForm(initial=initial)
            return render(request, CommentView.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])

    @staticmethod
    @exception_handler
    def edit(request, comment_id):
        """
        Comment forms populate attributes from GET parameters, so require the create
        method to be extended.
        """

        if not request.access_token:
            raise PermissionDenied

        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

        if request.method == 'POST':
            form = CommentForm(request.POST)
            if form.is_valid():
                comment_request = Comment.from_edit_form(form.cleaned_data)
                comment_response = comment_request.update(request.META['HTTP_HOST'], access_token=request.access_token)
                if comment_response.meta.links.get('via'):
                    return HttpResponseRedirect(CommentView.build_comment_location(comment_response))
                else:
                    return HttpResponseRedirect(reverse('single-comment', args=(comment_response.id,)))
            else:
                view_data['form'] = form
                return render(request, CommentView.form_template, view_data)

        elif request.method == 'GET':
            comment = Comment.retrieve(
                request.META['HTTP_HOST'],
                comment_id,
                access_token=request.access_token
            )
            view_data['form'] = CommentForm(comment.as_dict)
            return render(request, CommentView.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])

    @staticmethod
    @exception_handler
    def delete(request, comment_id):
        """
        Delete a comment and be redirected to the item.
        """

        if request.method == 'POST':
            comment = Comment.retrieve(request.META['HTTP_HOST'], comment_id, access_token=request.access_token)
            comment.delete(request.META['HTTP_HOST'], request.access_token)
            if comment.item_type == 'event':
                return HttpResponseRedirect(reverse('single-event', args=(comment.item_id,)))
            elif comment.item_type == 'conversation':
                return HttpResponseRedirect(reverse('single-conversation', args=(comment.item_id,)))
            else:
                return HttpResponseRedirect(reverse('microcosm-list'))
        else:
            return HttpResponseNotAllowed()


class AlertView(object):

    list_template = 'alerts.html'

    @staticmethod
    @exception_handler
    def list(request):

        if not request.access_token:
            raise HttpResponseNotAllowed

        # pagination offset
        offset = int(request.GET.get('offset', 0))

        url, params, headers = AlertList.build_request(
            request.META['HTTP_HOST'],
            offset=offset,
            access_token=request.access_token
        )
        request.view_requests.append(grequests.get(url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))
        alerts_list = AlertList(responses[url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'site': request.site,
            'content': alerts_list,
            'pagination': build_pagination_links(request, alerts_list.alerts)
        }

        return render(request, AlertView.list_template, view_data)

    @staticmethod
    @exception_handler
    def mark_viewed(request, alert_id):
        """
        Mark a notification as viewed by setting a 'viewed' attribute.
        """

        if request.method == 'POST':
            Alert.mark_viewed(request.META['HTTP_HOST'], alert_id, request.access_token)
            return HttpResponseRedirect(reverse('list-notifications'))
        else:
            return HttpResponseNotAllowed(['POST',])


class WatcherView(object):

    list_template = 'watchers.html'

    @staticmethod
    @exception_handler
    def list(request):

        if not request.access_token:
            raise HttpResponseNotAllowed

        if request.method == 'GET':
            # pagination offset
            offset = int(request.GET.get('offset', 0))

            url, params, headers = WatcherList.build_request(
                request.META['HTTP_HOST'],
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(grequests.get(url, params=params, headers=headers))
            responses = response_list_to_dict(grequests.map(request.view_requests))
            watchers_list = WatcherList(responses[url])

            view_data = {
                'user': Profile(responses[request.whoami_url], summary=False),
                'site': request.site,
                'content': watchers_list,
                'pagination': build_pagination_links(request, watchers_list.watchers)
            }

            return render(request, WatcherView.list_template, view_data)

        if request.method == 'POST':
            if 'watcher_id' in request.POST:
                watchers = request.POST.getlist('watcher_id')
                for w in watchers:
                    if request.POST.get('delete_watcher_' + str(w)):
                        Watcher.delete(request.META['HTTP_HOST'], w, request.access_token)
                    else:
                        postdata = {
                            'id': int(w),
                            'receiveEmail': bool(request.POST.get('receive_email_'+str(w))),
                            'receiveAlert': bool(request.POST.get('receive_alert_'+str(w))),
                            'receiveSMS': False,
                        }
                        Watcher.update(
                            request.META['HTTP_HOST'],
                            int(w),
                            postdata,
                            request.access_token
                        )
            return HttpResponseRedirect(reverse('list-watchers'))
        else:
            return HttpResponseNotAllowed(['POST',])


class AlertPreferenceView(object):

    list_template = 'alert_preferences.html'

    @staticmethod
    @exception_handler
    def settings(request):

        if not request.access_token:
            raise HttpResponseNotAllowed

        if request.method == 'GET':

            url, params, headers = AlertPreference.build_request(
                request.META['HTTP_HOST'],
                request.access_token
            )
            request.view_requests.append(grequests.get(url, params=params, headers=headers))
            url2, params2, headers2 = GlobalOptions.build_request(
                request.META['HTTP_HOST'],
                request.access_token
            )
            request.view_requests.append(grequests.get(url2, params=params2, headers=headers2))
            responses = response_list_to_dict(grequests.map(request.view_requests))
            preference_list = AlertPreference.from_list(responses[url])
            global_options = GlobalOptions.from_api_response(responses[url2])

            view_data = {
                'user': Profile(responses[request.whoami_url], summary=False),
                'site': request.site,
                'content': preference_list,
                'globaloptions': global_options,
            }
            return render(request, AlertPreferenceView.list_template, view_data)

        if request.method == 'POST':
            for x in range(1,10):
                if request.POST.get('alert_type_id_'+str(x)):
                    postdata = {
                        'alertTypeId': int(request.POST['alert_type_id_'+str(x)]),
                        'receiveEmail': bool(request.POST.get('receive_email_'+str(x))),
                        'receiveAlert': bool(request.POST.get('receive_alert_'+str(x))),
                        'receiveSMS': False,
                    }
                    AlertPreference.update(
                        request.META['HTTP_HOST'],
                        request.POST['alert_type_id_'+str(x)],
                        postdata,
                        request.access_token
                    )

            postdata = {
                'emailNotifications': bool(request.POST.get('profile_receive_email')),
                'alertNotifications': bool(request.POST.get('profile_receive_alert')),
                'smsNotifications': False,
            }
            GlobalOptions.update(
                request.META['HTTP_HOST'],
                postdata,
                request.access_token
            )
            return HttpResponseRedirect(reverse('notification-settings'))
        else:
            return HttpResponseNotAllowed()


class ErrorView(object):

    @staticmethod
    def not_found(request):
        # Only fetch the first element of view_requests (whoami)
        responses = response_list_to_dict(grequests.map(request.view_requests[:1]))
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': request.site
        }
        context = RequestContext(request, view_data)
        return HttpResponseNotFound(loader.get_template('404.html').render(context))

    @staticmethod
    def forbidden(request):
        view_data = {}
        # If fetching user login data results in HTTP 401, the access token is invalid
        try:
            # Only fetch the first element of view_requests (whoami)
            responses = response_list_to_dict(grequests.map(request.view_requests[:1]))
            view_data['user'] = Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None
        except APIException as e:
            if e.status_code == 401 or e.status_code == 403:
                view_data['logout'] = True
        view_data['site'] = request.site
        context = RequestContext(request, view_data)
        response = HttpResponseForbidden(loader.get_template('403.html').render(context))
        if view_data.get('logout'):
            response.delete_cookie('access_token')
        return response

    @staticmethod
    def server_error(request):
        # Only fetch the first element of view_requests (whoami)
        responses = response_list_to_dict(grequests.map(request.view_requests[:1]))
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': request.site,
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

        url = build_url(request.META['HTTP_HOST'], ['auth'])
        response = requests.post(url, data=data, headers={})
        access_token = response.json()['data']

        response = HttpResponseRedirect(target_url if target_url != '' else '/')
        response.set_cookie('access_token', access_token, httponly=True)
        return response

    @staticmethod
    @exception_handler
    def logout(request):
        """
        Log a user out. Issues a DELETE request to the backend for the
        user's access_token, and issues a delete cookie header in response to
        clear the user's access_token cookie.
        """

        view_data = dict(site=request.site)
        response = render(request, 'logout.html', view_data)

        if request.COOKIES.has_key('access_token'):
            response.delete_cookie('access_token')
            url = build_url(request.META['HTTP_HOST'], ['auth',request.access_token])
            requests.post(url, params={'method': 'DELETE', 'access_token': request.access_token})

        return response


class GeoView(object):

    @staticmethod
    @exception_handler
    def geocode(request):
        if request.access_token is None:
            raise PermissionDenied
        if request.GET.has_key('q'):
            response = GeoCode.retrieve(
                request.META['HTTP_HOST'],
                request.GET['q'],
                request.access_token
            )
            return HttpResponse(response, content_type='application/json')
        else:
            return HttpResponseBadRequest()


def echo_headers(request):
    view_data = '<html><body><table>'
    for key in request.META.keys():
        view_data += '<tr><td>%s</td><td>%s</td></tr>' % (key, request.META[key])
    view_data += '</table></body></html>'
    return HttpResponse(view_data, content_type='text/html')


class FaviconView(RedirectView):

    def get_redirect_url(self, **kwargs):
        return settings.STATIC_URL + '/img/favico.png'


class RobotsView(TemplateView):

    template = 'robots.txt'

    def get_context_data(self, **kwargs):
        return super(RobotsView, self).get_context_data(**kwargs)
