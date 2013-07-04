import requests

from functools import wraps
from microweb import settings
from microweb.settings import PAGE_SIZE
from microweb.helpers import join_path_fragments
from microweb.helpers import build_url
from urlparse import urlunparse

from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import HttpResponseBadRequest
from django.http import HttpResponse
from django.http import HttpResponseNotAllowed
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import render_to_response
from django.template import RequestContext

from microcosm.api.exceptions import APIException
from microcosm.api.resources import Microcosm
from microcosm.api.resources import MicrocosmList
from microcosm.api.resources import User
from microcosm.api.resources import GeoCode
from microcosm.api.resources import Event
from microcosm.api.resources import Comment
from microcosm.api.resources import Conversation
from microcosm.api.resources import Profile
from microcosm.api.resources import RESOURCE_PLURAL
from microcosm.api.resources import COMMENTABLE_ITEM_TYPES

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
            if e.status_code == 401:
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

        # Offset for paging of event comments
        offset = int(request.GET.get('offset', 0))
        conversation = Conversation.retrieve(
            request.META['HTTP_HOST'],
            id=conversation_id,
            offset=offset,
            access_token=request.access_token
        )
        comment_form = CommentForm(initial=dict(itemId=conversation_id, itemType='conversation'))

        view_data = {
            'user': request.whoami,
            'site': request.site,
            'content': conversation,
            'comment_form': comment_form,
            'pagination': build_pagination_links(request, conversation.comments)
        }

        return render(request, ConversationView.single_template, view_data)

    @staticmethod
    @exception_handler
    def create(request, microcosm_id):
        """
        Create a conversation.
        """

        view_data = dict(user=request.whoami, site=request.site)

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

        view_data = dict(user=request.whoami, site=request.site)

        if request.method == 'POST':
            form = ConversationView.edit_form(request.POST)

            if form.is_valid():
                conv_request = Conversation.from_edit_form(form.cleaned_data)
                conv_response = conv_request.update(request.META['HTTP_HOST'], conv_request.id, request.access_token)
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
            Conversation.delete(request.META['HTTP_HOST'], conversation_id, request.access_token)
            return HttpResponseRedirect(reverse('single-microcosm', args=(conversation.microcosm_id,)))
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

        view_data = dict(user=request.whoami, site=request.site)

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
        To edit a Profile, we must fetch the associated User object since the
        user's email is submitted as Profile.gravatar. This won't be needed when
        PATCH support is added.
        """

        view_data = dict(user=request.whoami, site=request.site)

        if request.method == 'POST':
            form = ProfileView.edit_form(request.POST)
            if form.is_valid():
                form_data = Profile(form.cleaned_data)
                profile = Profile.update(
                    request.META['HTTP_HOST'],
                    form_data.as_dict,
                    profile_id,
                    request.access_token
                )
                return HttpResponseRedirect(reverse('single-profile', args=(profile['id'],)))
            else:
                view_data['form'] = form
                return render(request, ProfileView.form_template, view_data)

        elif request.method == 'GET':
            user_private_details = User.retrieve(
                request.META['HTTP_HOST'],
                request.whoami.user_id,
                access_token=request.access_token
            )
            user_profile = Profile.retrieve(
                request.META['HTTP_HOST'],
                profile_id,
                request.access_token
            )
            user_profile.gravatar = user_private_details.email
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

        # record offset for paging of items within the microcosm
        offset = int(request.GET.get('offset', 0))

        microcosm = Microcosm.retrieve(
            request.META['HTTP_HOST'],
            id=microcosm_id,
            offset=offset,
            access_token=request.access_token
        )

        view_data = {
            'user': request.whoami,
            'site': request.site,
            'content': microcosm,
            'pagination': build_pagination_links(request, microcosm.items)
        }

        return render(request, MicrocosmView.single_template, view_data)

    @staticmethod
    @exception_handler
    def list(request):

        # record offset for paging of microcosms
        offset = int(request.GET.get('offset', 0))

        microcosm_list = MicrocosmList.retrieve(
            request.META['HTTP_HOST'],
            offset=offset,
            access_token=request.access_token
        )

        view_data = {
            'user': request.whoami,
            'site': request.site,
            'content': microcosm_list,
            'pagination': build_pagination_links(request, microcosm_list.microcosms)
        }

        return render(request, MicrocosmView.list_template, view_data)

    @staticmethod
    @exception_handler
    def create(request):

        view_data = dict(user=request.whoami, site=request.site)

        if request.method == 'POST':
            form = MicrocosmView.create_form(request.POST)
            if form.is_valid():
                form_data = Microcosm(form.cleaned_data)
                microcosm = Microcosm.create(
                    request.META['HTTP_HOST'],
                    form_data.as_dict,
                    request.access_token
                )
                return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm['id'],)))
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

        view_data = dict(user=request.whoami, site=request.site)

        if request.method == 'POST':
            form = MicrocosmView.edit_form(request.POST)
            if form.is_valid():
                form_data = Microcosm(form.cleaned_data)
                microcosm = Microcosm.update(
                    request.META['HTTP_HOST'],
                    form_data.as_dict,
                    microcosm_id,
                    request.access_token
                )
                return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm['id'],)))
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
            Microcosm.delete(request.META['HTTP_HOST'], microcosm_id, request.access_token)
            return HttpResponseRedirect(reverse(MicrocosmView.list))
        return HttpResponseNotAllowed(['POST'])

    @staticmethod
    @exception_handler
    def create_item_choice(request, microcosm_id):
        """
        Interstitial page for creating an item (e.g. Event) belonging to a microcosm.
        """

        microcosm = Microcosm.retrieve(
            request.META['HTTP_HOST'],
            microcosm_id,
            access_token=request.access_token
        )

        view_data = {
            'user' : request.whoami,
            'site' : request.site,
            'content' : microcosm
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

        # Offset for paging of event comments
        offset = int(request.GET.get('offset', 0))
        event = Event.retrieve(
            request.META['HTTP_HOST'],
            id=event_id,
            offset=offset,
            access_token=request.access_token
        )

        attendees = event.get_attendees(request.META['HTTP_HOST'], request.access_token)
        comment_form = CommentForm(initial=dict(itemId=event_id, itemType='event'))

        view_data = {
            'user': request.whoami,
            'site': request.site,
            'content': event,
            'comment_form': comment_form,
            'attendees': attendees,
            'pagination': build_pagination_links(request, event.comments)
        }

        return render(request, EventView.single_template, view_data)

    @staticmethod
    @exception_handler
    def create(request, microcosm_id):
        """
        Create an event within a microcosm.
        """

        view_data = dict(user=request.whoami, site=request.site)

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

        view_data = dict(user=request.whoami, site=request.site)

        if request.method == 'POST':
            form = EventView.edit_form(request.POST)
            if form.is_valid():
                event_request = Event.from_edit_form(form.cleaned_data)
                event_response = event_request.update(request.META['HTTP_HOST'], event_request.id, request.access_token)
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
            Event.delete(request.META['HTTP_HOST'], event_id, request.access_token)
            return HttpResponseRedirect(reverse('single-microcosm', args=(event.microcosm_id,)))
        else:
            return HttpResponseNotAllowed()

    @staticmethod
    def rsvp(request, event_id):
        """
        Create an attendee (RSVP) for an event. An attendee can be in one of four states:
        invited, confirmed, maybe, no.
        """

        if request.method == 'POST':
            if request.whoami:
                attendee = {
                    'RSVP' : request.POST['rsvp'],
                    'AttendeeId' : request.whoami.id
                }
                Event.rsvp(
                    request.META['HTTP_HOST'],
                    event_id,
                    request.whoami.id,
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

        comment = Comment.retrieve(
            request.META['HTTP_HOST'],
            id=comment_id,
            access_token=request.access_token
        )

        view_data = {
            'user': request.whoami,
            'site': request.site,
            'content': comment,
        }

        return render(request, CommentView.single_template, view_data)

    @staticmethod
    @exception_handler
    def create(request):
        """
        Comment forms populate attributes from GET parameters, so require the create
        method to be extended.
        """

        view_data = dict(user=request.whoami, site=request.site)

        if request.method == 'POST':
            form = CommentForm(request.POST)
            if form.is_valid():
                comment = Comment.create(
                    request.META['HTTP_HOST'],
                    data=form.cleaned_data,
                    access_token=request.access_token
                )

                if comment.meta.links.get('via'):
                    return HttpResponseRedirect(CommentView.build_comment_location(comment))
                else:
                    return HttpResponseRedirect(reverse('single-comment', args=(comment.id,)))
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

        view_data = dict(user=request.whoami, site=request.site)

        if request.method == 'POST':
            form = CommentForm(request.POST)
            if form.is_valid():
                comment = Comment.update(
                    request.META['HTTP_HOST'],
                    form.cleaned_data,
                    comment_id,
                    request.access_token
                )
                if comment.meta.links.get('via'):
                    return HttpResponseRedirect(CommentView.build_comment_location(comment))
                else:
                    return HttpResponseRedirect(reverse('single-comment', args=(comment.id,)))
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
            Comment.delete(request.META['HTTP_HOST'], comment_id, request.access_token)
            if comment.item_type == 'event':
                return HttpResponseRedirect(reverse('single-event', args=(comment.item_id,)))
            elif comment.item_type == 'conversation':
                return HttpResponseRedirect(reverse('single-conversation', args=(comment.item_id,)))
            else:
                return HttpResponseRedirect(reverse('microcosm-list'))
        else:
            return HttpResponseNotAllowed()


class ErrorView(object):

    @staticmethod
    def not_found(request):
        view_data = dict(site=request.site, user=request.whoami)
        return render(request, '404.html', view_data)

    @staticmethod
    def forbidden(request):
        view_data = dict(site=request.site,user=request.whoami)
        return render(request, '403.html', view_data)

    @staticmethod
    def server_error(request):
        return render_to_response('500.html',
            context_instance = RequestContext(request)
        )


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
        headers= {'Host': request.META.get('HTTP_HOST')}

        access_token = requests.post(build_url(request.META['HTTP_HOST'], ['auth']), data=data, headers=headers).json()['data']

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
