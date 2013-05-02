import traceback
import logging
import requests

from functools import wraps
from microweb import settings

from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseBadRequest
from django.http import HttpResponse
from django.http import HttpResponseNotAllowed
from django.http import HttpResponseRedirect
from django.shortcuts import render

from microcosm.api.exceptions import APIException
from microcosm.api.resources import Microcosm, User, GeoCode
from microcosm.api.resources import Event
from microcosm.api.resources import Comment
from microcosm.api.resources import Conversation
from microcosm.api.resources import Profile
from microcosm.api.resources import Authentication

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
            logging.error(traceback.format_exc())
            if e.status_code == 401:
                raise PermissionDenied
            elif e.status_code == 404:
                raise Http404
            else:
                raise
    return decorator


class ItemView(object):
    """
    A base view class that provides generic create/read/update methods and single item or list views.
    This class shouldn't be used directly, it should be subclassed.
    """

    commentable = False

    @classmethod
    @exception_handler
    def create(cls, request, microcosm_id=None):
        """
        Generic method for creating microcosms and items within microcosms.

        microcosm_id only needs to be provided if an item is being created
        within a microcosm (e.g. a conversation or event).
        """

        view_data = {
            'user': request.whoami,
            'site': request.site,
        }

        # Populate form from POST data, return populated form if not valid
        if request.method == 'POST':
            form = cls.create_form(request.POST)
            if form.is_valid():
                item = cls.resource_cls.create(form.cleaned_data, request.access_token)
                return HttpResponseRedirect('/%s/%d' % (cls.item_plural, item['id']))
            else:
                view_data['form'] = form
                return render(request, cls.form_template, view_data)

        # Render form for creating a new item
        elif request.method == 'GET':
            initial = {}
            # If a microcosm_id is provided, this must be pre-populated in the item form
            if microcosm_id:
                initial['microcosmId'] = microcosm_id
            view_data['form'] = cls.create_form(initial=initial)
            return render(request, cls.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])

    @classmethod
    @exception_handler
    def edit(cls, request, item_id):
        """
        Generic edit view. The item with item_id is used to populate form fields.
        """

        view_data = {
            'user': request.whoami,
            'site': request.site,
        }

        # Populate form from POST data, return populated form if not valid
        if request.method == 'POST':
            form = cls.edit_form(request.POST)
            if form.is_valid():
                form_data = form.cleaned_data
                # API expects editReason wrapped in a 'meta' object
                if form_data.has_key('editReason'):
                    form_data['meta'] =  {'editReason': form_data['editReason']}
                item = cls.resource_cls.update(form_data, item_id, request.access_token)
                return HttpResponseRedirect('/%s/%d' % (cls.item_plural, item['id']))
            else:
                view_data['form'] = form
                return render(request, cls.form_template, view_data)

        # Populate form with item data
        elif request.method == 'GET':
            item = cls.resource_cls.retrieve(id=item_id, access_token=request.access_token)
            view_data['form'] = cls.edit_form(item)
            return render(request, cls.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])

    @classmethod
    @exception_handler
    def single(cls, request, item_id):
        """
        Generic method for displaying a single item.
        """

        # Offset for paging of item comments
        offset = int(request.GET.get('offset', 0))

        content = cls.resource_cls.retrieve(
            id=item_id,
            offset=offset,
            access_token=request.access_token
        )

        view_data = {
            'user': request.whoami,
            'site': request.site,
            'item_type': cls.item_type,
            'content': content,
            'pagination': {},
        }

        if content.has_key('comments') or content.has_key('items'):
            cls.build_pagination_nav(request.path, content, view_data, offset)

        # Provide a comment form for items that allow comments
        if cls.commentable:
            comment_form = CommentForm(
                initial = {
                    'itemId': item_id,
                    'itemType': cls.item_type,
                    'targetUrl': '/%s/%s' % (cls.item_plural, item_id),
                }
            )
            view_data['comment_form'] = comment_form

        # Composition of any other elements, e.g. attendees or poll choices
        if hasattr(cls, 'extra_item_data') and callable(cls.extra_item_data):
            view_data = cls.extra_item_data(
                item_id,
                view_data,
                request.access_token
            )

        return render(request, cls.one_template, view_data)

    @classmethod
    @exception_handler
    def list(cls, request):
        """
        Generic method for displaying a list of items.
        """

        # Pagination offset
        offset = int(request.GET.get('offset', 0))

        list = cls.resource_cls.retrieve(offset=offset, access_token=request.access_token)

        view_data = {
            'user': request.whoami,
            'site': request.site,
            'content': list,
            'pagination': {},
        }

        cls.build_pagination_nav(request.path, list, view_data, offset)

        return render(request, cls.many_template, view_data)

    @classmethod
    @exception_handler
    def delete(cls, request, item_id):
        """
        Generic method for deleting a single item (deletion of a list is not yet implemented).
        """

        if request.method == 'POST':
            cls.resource_cls.delete(item_id, request.access_token)
            redirect = request.POST.get('targetUrl', None) or reverse(MicrocosmView.list)
            return HttpResponseRedirect(redirect)
        else:
            return HttpResponseNotAllowed()

    @classmethod
    def build_pagination_nav(cls, path, resource, view_data, offset):

        paginated_list = None

        # Single item, which has comments or microcosms
        if resource.has_key('id'):
            if resource.get('comments', None):
                paginated_list = resource['comments']
            elif resource.get('items', None):
                paginated_list = resource['items']
        # Collection of items
        elif resource.has_key(cls.item_plural):
            if resource.get(cls.item_plural, None):
                paginated_list = resource.get(cls.item_plural)
        else:
            return

        # Maximum record offset is (no. of pages - 1) multiplied by page size
        # TODO: this will be unecessary when max_offset is added to responses
        max_offset = (paginated_list['pages'] - 1) * paginated_list['limit']

        # TODO: remove implicit dependency on linkmap transformer
        if paginated_list['linkmap'].has_key('first'):
            view_data['pagination']['first'] = path
        if paginated_list['linkmap'].has_key('prev'):
            view_data['pagination']['prev'] = path + '?offset=%d' % (offset - settings.PAGE_SIZE)
        if paginated_list['linkmap'].has_key('next'):
            view_data['pagination']['next'] = path + '?offset=%d' % (offset + settings.PAGE_SIZE)
        if paginated_list['linkmap'].has_key('last'):
            view_data['pagination']['last'] = path + '?offset=%d' % max_offset


class ConversationView(ItemView):

    item_type = 'conversation'
    item_plural = 'conversations'
    resource_cls = Conversation
    create_form = ConversationCreate
    edit_form = ConversationEdit
    form_template = 'forms/conversation.html'
    one_template = 'conversation.html'
    commentable = True


class ProfileView(ItemView):

    item_type = 'profile'
    item_plural = 'profiles'
    resource_cls = Profile
    edit_form = ProfileEdit
    form_template = 'forms/profile.html'
    one_template = 'profile.html'

    @classmethod
    @exception_handler
    def edit(cls, request, item_id):

        """
        We need to fetch a 'user' object to edit their profile, since the
        user's email is submitted as 'gravatar'. This won't be needed when
        PATCH support is added.
        """

        view_data = {
            'user': request.whoami,
            'site': request.site,
        }

        # Populate form from POST data, return populated form if not valid
        if request.method == 'POST':
            form = cls.edit_form(request.POST)
            if form.is_valid():
                form_data = form.cleaned_data
                item = cls.resource_cls.update(form_data, item_id, request.access_token)
                return HttpResponseRedirect('/%s/%d' % (cls.item_plural, item['id']))
            else:
                view_data['form'] = form
                return render(request, cls.form_template, view_data)

        # Populate form with item data
        elif request.method == 'GET':
            user_private_details = User.retrieve(request.whoami['id'], access_token=request.access_token)
            user_profile = cls.resource_cls.retrieve(id=item_id, access_token=request.access_token)
            if user_private_details.has_key('email'):
                user_profile['gravatar'] = user_private_details['email']
            view_data['form'] = cls.edit_form(user_profile)
            return render(request, cls.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])


class MicrocosmView(ItemView):

    item_type = 'microcosm'
    item_plural = 'microcosms'
    resource_cls = Microcosm
    create_form = MicrocosmCreate
    edit_form = MicrocosmEdit
    form_template = 'forms/microcosm.html'
    one_template = 'microcosm.html'
    many_template = 'microcosms.html'

    @classmethod
    @exception_handler
    def create_item_choice(cls, request, microcosm_id):
        """
        Interstitial page for creating an item (e.g. Event) belonging to a microcosm.
        """

        microcosm = cls.resource_cls.retrieve(microcosm_id, access_token=request.access_token)

        view_data = {
            'user' : request.whoami,
            'site' : request.site,
            'content' : microcosm
        }

        return render(request, 'create_item_choice.html', view_data)


class EventView(ItemView):

    item_type = 'event'
    item_plural = 'events'
    resource_cls = Event
    create_form = EventCreate
    edit_form = EventEdit
    form_template = 'forms/event.html'
    one_template = 'event.html'
    commentable = True

    @classmethod
    def extra_item_data(cls, event_id, view_data, access_token=None):
        view_data['attendees'] = cls.resource_cls.retrieve_attendees(
            event_id, access_token)
        return view_data

    @classmethod
    def rsvp(cls, request, event_id):
        """
        Create an attendee (RSVP) for an event. An attendee can be in one of four states:
        invited, confirmed, maybe, no.
        """

        if request.method == 'POST':
            if request.whoami:
                attendee = {
                    'RSVP' : request.POST['rsvp'],
                    'AttendeeId' : request.whoami['id']
                }
                cls.resource_cls.rsvp(event_id, request.whoami['id'], attendee, access_token=request.access_token)
                return HttpResponseRedirect('/events/%s' % event_id)
            else:
                raise PermissionDenied
        else:
            raise HttpResponseNotAllowed(['POST'])


class CommentView(ItemView):

    item_type = 'comment'
    item_plural = 'comments'
    resource_cls = Comment
    create_form = CommentForm
    edit_form = CommentForm
    form_template = 'forms/create_comment.html'
    one_template = 'comment.html'

    @staticmethod
    def fill_from_get(request, initial):
        """
        Utility for populating form fields from GET parameters
        """

        if request.GET.has_key('targetUrl'):
            initial['targetUrl'] = request.GET.get('targetUrl', None)
        if request.GET.has_key('itemId'):
            initial['itemId'] = request.GET.get('itemId', None)
        if request.GET.has_key('itemType'):
            initial['itemType'] = request.GET.get('itemType', None)
        if request.GET.has_key('inReplyTo'):
            initial['inReplyTo'] = request.GET.get('inReplyTo', None)

        return initial

    @classmethod
    @exception_handler
    def create(cls, request):
        """
        Comment forms populate attributes from GET parameters, so require the create
        method to be extended.
        """

        view_data = {
            'user': request.whoami,
            'site': request.site,
        }

        if request.method == 'POST':
            form = cls.create_form(request.POST)
            if form.is_valid():
                item = cls.resource_cls.create(data=form.cleaned_data, access_token=request.access_token)
                # If a targetUrl has not been provided, redirect to /comments/{id}
                if request.POST['targetUrl'] != '':
                    return HttpResponseRedirect(request.POST['targetUrl'])
                if request.GET['targetUrl'] != '':
                    return HttpResponseRedirect(request.GET['targetUrl'])
                else:
                    return HttpResponseRedirect('/%s/%d' % (cls.item_plural, item['id']))
            else:
                view_data['form'] = form
                return render(request, cls.form_template, view_data)

        elif request.method == 'GET':
            initial = CommentView.fill_from_get(request, {})
            view_data['form'] = cls.create_form(initial=initial)
            return render(request, cls.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])

    @classmethod
    @exception_handler
    def edit(cls, request, item_id):
        """
        Comment forms populate attributes from GET parameters, so require the create
        method to be extended.
        """

        view_data = {
            'user': request.whoami,
            'site': request.site,
        }

        if request.method == 'POST':
            form = cls.create_form(request.POST)
            if form.is_valid():
                item = cls.resource_cls.update(form.cleaned_data, item_id, request.access_token)
                # If a targetUrl has not been provided, redirect to /comments/{id}
                if request.POST['targetUrl'] != '':
                    return HttpResponseRedirect(request.POST['targetUrl'])
                if request.GET['targetUrl'] != '':
                    return HttpResponseRedirect(request.GET['targetUrl'])
                else:
                    return HttpResponseRedirect(''.join(['/', cls.item_plural, '/', str(item['id'])]))
            else:
                view_data['form'] = form
                return render(request, cls.form_template, view_data)

        elif request.method == 'GET':
            comment = cls.resource_cls.retrieve(item_id, access_token=request.access_token)
            initial = CommentView.fill_from_get(request, {})
            if initial.has_key('targetUrl'): comment['targetUrl'] = initial['targetUrl']
            view_data['form'] = cls.edit_form(comment)
            return render(request, cls.form_template, view_data)

        else:
            return HttpResponseNotAllowed(['GET', 'POST'])


class ErrorView():

    @staticmethod
    def not_found(request):

        view_data = {
            'site' : request.site,
            'user' : request.whoami,
        }
        return render(request, '404.html', view_data)

    @staticmethod
    def forbidden(request):

        view_data = {
            'site' : request.site,
            'user' : request.whoami,
        }
        return render(request, '403.html', view_data)


class AuthenticationView():

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
        client_secret = settings.CLIENT_SECRET

        data = {
            "Assertion": assertion,
            "ClientSecret": client_secret
        }
        headers= {'Host': request.META.get('HTTP_HOST')}

        access_token = Authentication.create(data, headers=headers)
        response = HttpResponseRedirect(target_url)
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

        view_data = {
            'site': request.site,
        }

        response = render(request, 'logout.html', view_data)

        if request.COOKIES.has_key('access_token'):
            response.delete_cookie('access_token')
            url = settings.API_ROOT + 'auth/%s' % request.access_token
            requests.post(url, params={'method': 'DELETE', 'access_token': request.access_token})

        return response


class GeoView():

    @staticmethod
    @exception_handler
    def geocode(request):
        if request.access_token is None:
            raise PermissionDenied
        if request.GET.has_key('q'):
            response = GeoCode.retrieve(request.GET['q'], request.access_token)
            return HttpResponse(response, content_type='application/json')
        else:
            return HttpResponseBadRequest()


def echo_headers(request):

    view_data = request.META
    return HttpResponse(str(view_data))
