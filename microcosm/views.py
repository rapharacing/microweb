import requests
import grequests
import string
import datetime
import json
import logging

from functools import wraps

from urllib import urlencode

from urlparse import parse_qs
from urlparse import urlparse
from urlparse import urlunparse

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
from microcosm.api.resources import Microcosm
from microcosm.api.resources import MicrocosmList
from microcosm.api.resources import Role
from microcosm.api.resources import RoleCriteria
from microcosm.api.resources import RoleCriteriaList
from microcosm.api.resources import RoleList
from microcosm.api.resources import RoleProfile
from microcosm.api.resources import RoleProfileList
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
from microcosm.api.resources import RESOURCE_PLURAL
from microcosm.api.resources import COMMENTABLE_ITEM_TYPES
from microcosm.api.resources import response_list_to_dict
from microcosm.api.resources import GlobalOptions
from microcosm.api.resources import ProfileList
from microcosm.api.resources import Search
from microcosm.api.resources import Site
from microcosm.api.resources import Huddle
from microcosm.api.resources import HuddleList
from microcosm.api.resources import Trending
from microcosm.api.resources import Legal

from microcosm.api.resources import build_url
from microcosm.api.resources import join_path_fragments

from microcosm.forms.forms import MicrocosmCreate
from microcosm.forms.forms import MicrocosmEdit

from microcosm.forms.forms import CommentForm
from microcosm.forms.forms import ProfileEdit
from microcosm.forms.forms import HuddleCreate
from microcosm.forms.forms import HuddleEdit

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


class HuddleView(object):
    create_form = HuddleCreate
    edit_form = HuddleEdit
    form_template = 'forms/huddle.html'
    single_template = 'huddle.html'
    list_template = 'huddles.html'

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET',])
    def single(request, huddle_id):

        # Comment offset.
        offset = int(request.GET.get('offset', 0))

        huddle_url, params, headers = Huddle.build_request(request.get_host(), id=huddle_id, offset=offset,
            access_token=request.access_token)
        request.view_requests.append(grequests.get(huddle_url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))
        huddle = Huddle.from_api_response(responses[huddle_url])
        comment_form = CommentForm(initial=dict(itemId=huddle_id, itemType='huddle'))

        # Fetch attachments.
        attachments = {}
        for comment in huddle.comments.items:
            c = comment.as_dict
            if 'attachments' in c:
                c_attachments = Attachment.retrieve(request.get_host(), "comments", c['id'],
                    access_token=request.access_token)
                attachments[str(c['id'])] = c_attachments

        # Fetch huddle participants.
        participants_json = [p.as_dict for p in huddle.participants]

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': huddle,
            'comment_form': comment_form,
            'pagination': build_pagination_links(responses[huddle_url]['comments']['links'], huddle.comments),
            'item_type': 'huddle',
            'attachments': attachments,
            'participants_json': json.dumps(participants_json)
        }

        return render(request, HuddleView.single_template, view_data)


    @staticmethod
    @exception_handler
    @require_http_methods(['GET',])
    def list(request):
        # record offset for paging of huddles
        offset = int(request.GET.get('offset', 0))

        huddle_url, params, headers = HuddleList.build_request(request.get_host(), offset=offset,
            access_token=request.access_token)

        request.view_requests.append(grequests.get(huddle_url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))

        huddles = HuddleList(responses[huddle_url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': huddles,
            'pagination': build_pagination_links(responses[huddle_url]['huddles']['links'], huddles.huddles)
        }
        return render(request, HuddleView.list_template, view_data)


    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET', 'POST',])
    def create(request):
        """
        Create a huddle.
        """

        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'site': Site(responses[request.site_url]),
        }

        if request.method == 'POST':
            form = HuddleView.create_form(request.POST)
            if form.is_valid():
                hud_request = Huddle.from_create_form(form.cleaned_data)
                hud_response = hud_request.create(request.get_host(), request.access_token)
                if hud_response.id > 0:
                    if request.POST.get('invite'):
                        ids = [int(x) for x in request.POST.get('invite').split(',')]
                        Huddle.invite(request.get_host(), hud_response.id, ids, request.access_token)

                    if request.POST.get('firstcomment') and len(request.POST.get('firstcomment')) > 0:
                        payload = {
                        'itemType': 'huddle',
                        'itemId': hud_response.id,
                        'markdown': request.POST.get('firstcomment'),
                        'inReplyTo': 0
                        }
                        comment = Comment.from_create_form(payload)
                        comment.create(request.get_host(), request.access_token)
                    return HttpResponseRedirect(reverse('single-huddle', args=(hud_response.id,)))
            else:
                view_data['form'] = form
                return render(request, HuddleView.form_template, view_data)

        if request.method == 'GET':
            if request.GET.get('to'):
                recipients = []
                list_of_recipient_ids = request.GET.get('to').split(",");

                for recipient_id in list_of_recipient_ids:
                    recipient_profile = Profile.retrieve(request.get_host(), recipient_id)
                    if recipient_profile.id > 0:
                        recipients.append({
                        'id': recipient_profile.id,
                        'profileName': recipient_profile.profile_name,
                        'avatar': recipient_profile.avatar
                        })

                view_data['recipients_json'] = json.dumps(recipients)

            view_data['form'] = HuddleView.create_form(initial=dict())
            return render(request, HuddleView.form_template, view_data)


    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['POST', ])
    def invite(request, huddle_id):
        """
        Invite participants to a huddle.
        """

        ids = [int(x) for x in request.POST.get('invite_profile_id').split()]
        Huddle.invite(request.get_host(), huddle_id, ids, request.access_token)
        return HttpResponseRedirect(reverse('single-huddle', args=(huddle_id,)))


    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['POST', ])
    def delete(request, huddle_id):
        """
        Delete a huddle and be redirected to the parent microcosm.
        """

        huddle = Huddle.retrieve(request.get_host(), huddle_id, access_token=request.access_token)
        huddle.delete(request.get_host(), request.access_token)
        return HttpResponseRedirect(reverse('list-huddle'))


    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET', ])
    def newest(request, huddle_id):
        """
        Get redirected to the first unread post in a huddle
        """

        response = Huddle.newest(request.get_host(), huddle_id, access_token=request.access_token)
        #because redirects are always followed, we can't just get the 'location' value
        response = response['comments']['links']
        for link in response:
            if link['rel'] == 'self':
                response = link['href']
        response = str.replace(str(response), '/api/v1', '')
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
        response = urlunparse((pr[0], pr[1], pr[2], pr[3], queries, frag))
        return HttpResponseRedirect(response)


class ProfileView(object):
    edit_form = ProfileEdit
    form_template = 'forms/profile.html'
    single_template = 'profile.html'
    list_template = 'profiles.html'

    @staticmethod
    @exception_handler
    @require_http_methods(['GET', ])
    def single(request, profile_id):
        """
        Display a single profile by ID.
        """

        # Search
        search_q = 'type:microcosm type:conversation type:event type:comment authorId:%s' % profile_id
        search_params = {'limit': 5, 'q': search_q, 'sort': 'date'}
        search_url, params, headers = Search.build_request(request.get_host(), search_params,
            access_token=request.access_token)
        request.view_requests.append(grequests.get(search_url, params=params, headers=headers))

        # Profile
        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'item_type': 'profile',
            'site': Site(responses[request.site_url]),
            'search': Search.from_api_response(responses[search_url]),
            'site_section': 'people'
        }

        profile = Profile.retrieve(request.get_host(), profile_id, request.access_token)
        view_data['content'] = profile
        return render(request, ProfileView.single_template, view_data)

    @staticmethod
    @exception_handler
    @require_http_methods(['GET', ])
    def list(request):

        # Record offset for paging of profiles.
        offset = int(request.GET.get('offset', 0))
        top = bool(request.GET.get('top', False))
        q = request.GET.get('q', "")
        following = bool(request.GET.get('following', False))
        online = bool(request.GET.get('online', False))

        profiles_url, params, headers = ProfileList.build_request(request.get_host(), offset=offset, top=top,
            q=q, following=following, online=online, access_token=request.access_token)

        request.view_requests.append(grequests.get(profiles_url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))

        profiles = ProfileList(responses[profiles_url])

        subtitle = False
        if q != "" and len(q) == 1:
            subtitle = "names starting with %s" % (q.upper())

        filter_name = []

        if following:
            filter_name.append("following")

        if online:
            filter_name.append("online now")

        if top:
            filter_name.append("most comments")

        if len(filter_name) < 1:
            filter_name.append("sorted alphabetically")

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': profiles,
            'pagination': build_pagination_links(responses[profiles_url]['profiles']['links'], profiles.profiles),
            'q': q,
            'top': top,
            'following': following,
            'alphabet': string.ascii_lowercase,
            'site_section': 'people',
            'filter_name': ", ".join(filter_name),
            'subtitle': subtitle,
            'online': online
        }

        return render(request, ProfileView.list_template, view_data)

    @staticmethod
    @exception_handler
    @require_http_methods(['GET', 'POST',])
    def edit(request, profile_id):
        """
        Edit a user profile (profile name or avatar).
        """

        responses = response_list_to_dict(grequests.map(request.view_requests))
        user = Profile(responses[request.whoami_url], summary=False)
        view_data = {
            'user': user,
            'site': Site(responses[request.site_url]),
        }

        if request.method == 'POST':
            form = ProfileView.edit_form(request.POST)
            if form.is_valid():
                if request.FILES.has_key('avatar'):
                    file_request = FileMetadata.from_create_form(request.FILES['avatar'])
                    file_metadata = file_request.create(request.get_host(), request.access_token, 100, 100)
                    Attachment.create(
                        request.get_host(),
                        file_metadata.file_hash,
                        profile_id=user.id,
                        access_token=request.access_token,
                        file_name=request.FILES['avatar'].name
                    )
                profile_request = Profile(form.cleaned_data)
                profile_response = profile_request.update(request.get_host(), request.access_token)

                # Check for existing comment attached to profile.
                if request.POST.get('markdown'):
                    payload = {
                        'itemType': 'profile',
                        'itemId': profile_response.id,
                        'markdown': request.POST.get('markdown'),
                        'inReplyTo': 0
                    }

                    # Create new comment or edit the existing one.
                    if hasattr(profile_response, 'profile_comment'):
                        payload['id'] = profile_response.profile_comment.id
                        if len(request.POST.get('markdown')) < 1:
                            payload['markdown'] = ""
                        comment_request = Comment.from_edit_form(payload)
                        comment_request.update(request.get_host(), access_token=request.access_token)
                    else:
                        if len(request.POST.get('markdown')) > 0:
                            comment = Comment.from_create_form(payload)
                            comment.create(request.get_host(), request.access_token)

                return HttpResponseRedirect(reverse('single-profile', args=(profile_response.id,)))
            else:
                view_data['form'] = form
                return render(request, ProfileView.form_template, view_data)

        if request.method == 'GET':
            user_profile = Profile.retrieve(request.get_host(), profile_id, request.access_token)
            view_data['form'] = ProfileView.edit_form(user_profile.as_dict)
            return render(request, ProfileView.form_template, view_data)


class MicrocosmView(object):
    create_form = MicrocosmCreate
    edit_form = MicrocosmEdit
    form_template = 'forms/microcosm.html'
    single_template = 'microcosm.html'
    list_template = 'microcosms.html'

    @staticmethod
    @exception_handler
    @require_http_methods(['GET',])
    def single(request, microcosm_id):

        # Pagination offset of items within the microcosm.
        offset = int(request.GET.get('offset', 0))

        microcosm_url, params, headers = Microcosm.build_request(request.get_host(), id=microcosm_id,
            offset=offset, access_token=request.access_token)
        request.view_requests.append(grequests.get(microcosm_url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))
        microcosm = Microcosm.from_api_response(responses[microcosm_url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': microcosm,
            'item_type': 'microcosm',
            'pagination': build_pagination_links(responses[microcosm_url]['items']['links'], microcosm.items)
        }

        return render(request, MicrocosmView.single_template, view_data)

    @staticmethod
    @exception_handler
    @require_http_methods(['GET',])
    def list(request):

        # Pagination offset of microcosms.
        offset = int(request.GET.get('offset', 0))

        microcosms_url, params, headers = MicrocosmList.build_request(request.get_host(), offset=offset,
            access_token=request.access_token)
        request.view_requests.append(grequests.get(microcosms_url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))

        microcosms = MicrocosmList(responses[microcosms_url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': microcosms,
            'item_type': 'site',
            'pagination': build_pagination_links(responses[microcosms_url]['microcosms']['links'], microcosms.microcosms)
        }

        return render(request, MicrocosmView.list_template, view_data)

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET', 'POST',])
    def create(request):
        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'site': Site(responses[request.site_url]),
        }

        if request.method == 'POST':
            form = MicrocosmView.create_form(request.POST)
            if form.is_valid():
                microcosm_request = Microcosm.from_create_form(form.cleaned_data)
                microcosm_response = microcosm_request.create(request.get_host(), request.access_token)
                return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm_response.id,)))
            else:
                view_data['form'] = form
                return render(request, MicrocosmView.form_template, view_data)

        if request.method == 'GET':
            view_data['form'] = MicrocosmView.create_form()
            return render(request, MicrocosmView.form_template, view_data)


    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET', 'POST',])
    def edit(request, microcosm_id):
        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'site': Site(responses[request.site_url]),
        }

        if request.method == 'POST':
            form = MicrocosmView.edit_form(request.POST)
            if form.is_valid():
                microcosm_request = Microcosm.from_edit_form(form.cleaned_data)
                microcosm_response = microcosm_request.update(request.get_host(), request.access_token)
                return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm_response.id,)))
            else:
                view_data['form'] = form
                return render(request, MicrocosmView.form_template, view_data)

        if request.method == 'GET':
            microcosm = Microcosm.retrieve(request.get_host(), id=microcosm_id, access_token=request.access_token)
            view_data['form'] = MicrocosmView.edit_form(microcosm.as_dict)
            return render(request, MicrocosmView.form_template, view_data)


    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['POST',])
    def delete(request, microcosm_id):
        microcosm = Microcosm.retrieve(request.get_host(), microcosm_id, access_token=request.access_token)
        microcosm.delete(request.get_host(), request.access_token)
        return HttpResponseRedirect(reverse(MicrocosmView.list))


class MembershipView(object):
    list_template = 'memberships.html'
    form_template = 'forms/memberships.html'

    @staticmethod
    @exception_handler
    @require_http_methods(['GET',])
    def list(request, microcosm_id):
        offset = int(request.GET.get('offset', 0))

        microcosm_url, params, headers = Microcosm.build_request(
            request.get_host(),
            id=microcosm_id,
            offset=offset,
            access_token=request.access_token
        )
        request.view_requests.append(
            grequests.get(microcosm_url, params=params, headers=headers)
        )
        responses = response_list_to_dict(grequests.map(request.view_requests))
        microcosm = Microcosm.from_api_response(responses[microcosm_url])

        roles_url, params, headers = RoleList.build_request(
            request.META['HTTP_HOST'],
            id=microcosm_id,
            offset=offset,
            access_token=request.access_token
        )
        request.view_requests.append(
            grequests.get(roles_url, params=params, headers=headers)
        )
        responses = response_list_to_dict(grequests.map(request.view_requests))
        roles = RoleList.from_api_response(responses[roles_url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'site_section': 'memberships',
            'content': microcosm,
            'memberships': roles,
            'item_type': 'microcosm',
            'pagination': build_pagination_links(responses[microcosm_url]['items']['links'], microcosm.items)
        }

        return render(request, MembershipView.list_template, view_data)

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['POST',])
    def api(request, microcosm_id):

        data = json.loads(request.body)

        if data.has_key('role'):
            role = Role.from_summary(data['role'])
            role.microcosm_id = int(microcosm_id)

            if role.id == 0:
                response = Role.create_api(request.get_host(), role, request.access_token)
                if response.status_code != requests.codes.ok:
                    return HttpResponseBadRequest()
                role = Role.from_summary(response.json()['data'])
            else:
                response = Role.update_api(request.get_host(), role, request.access_token)
                if response.status_code != requests.codes.ok:
                    return HttpResponseBadRequest()
                role = Role.from_summary(response.json()['data'])

            # Do we have criteria
            if data.has_key('criteria') and len(data['criteria']) > 0:
                # Loop
                for clob in data['criteria']:
                    crit = RoleCriteria.from_summary(clob)

                    if crit.id == 0:
                        response = RoleCriteria.create_api(request.get_host(), role.microcosm_id, role.id, crit, request.access_token)
                        if response.status_code != requests.codes.ok:
                            return HttpResponseBadRequest()
                        crit = RoleCriteria.from_summary(response.json()['data'])
                    else:
                        response = RoleCriteria.update_api(request.get_host(), role.microcosm_id, role.id, crit, request.access_token)
                        if response.status_code != requests.codes.ok:
                            return HttpResponseBadRequest()
                        crit = RoleCriteria.from_summary(response.json()['data'])
            else:
                # Delete all criteria
                # Check response, if 200 continue other return JSON error
                # TODO: Is there an endpoint to delete all criteria?
                if response.status_code != requests.codes.ok:
                    return HttpResponseBadRequest()

            if data.has_key('profiles') and len(data['profiles']) > 0:
                # Loop
                pids = []
                for pid in data['profiles']:
                    pids.append({'id': int(pid)})

                response = RoleProfile.update_api(request.get_host(), role.microcosm_id, role.id, pids, request.access_token)
                if response.status_code != requests.codes.ok:
                    return HttpResponseBadRequest()

            else:
                # Delete all profiles
                # Check response, if 200 continue other return JSON error
                # TODO: Is there an endpoint to delete all criteria?
                if response.status_code != requests.codes.ok:
                    return HttpResponseBadRequest()

            # Need to return a stub here to allow the callee (AJAX) to be happy
            return HttpResponse('{"context": "","status": 200,"data": {}, "error": null}')
        else:
            return HttpResponseBadRequest()

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET', 'POST',])
    def create(request, microcosm_id):
        if request.method == 'POST':
            pass
        elif request.method == 'GET':
            offset = int(request.GET.get('offset', 0))

            microcosm_url, params, headers = Microcosm.build_request(
                request.get_host(),
                id=microcosm_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(
                grequests.get(microcosm_url, params=params, headers=headers)
            )
            responses = response_list_to_dict(grequests.map(request.view_requests))
            microcosm = Microcosm.from_api_response(responses[microcosm_url])

            roles_url, params, headers = RoleList.build_request(
                request.META['HTTP_HOST'],
                id=microcosm_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(
                grequests.get(roles_url, params=params, headers=headers)
            )
            responses = response_list_to_dict(grequests.map(request.view_requests))
            roles = RoleList.from_api_response(responses[roles_url])

            view_data = {
                'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
                'site': Site(responses[request.site_url]),
                'site_section': 'memberships',
                'content': microcosm,
                'item_type': 'memberships',
                'pagination': build_pagination_links(responses[microcosm_url]['items']['links'], microcosm.items)
            }

            return render(request, MembershipView.form_template, view_data)

    @staticmethod
    @exception_handler
    def edit(request, microcosm_id, group_id):

        if request.method == 'POST':
            pass
        elif request.method == 'GET':

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

            role_url, params, headers = Role.build_request(
                request.META['HTTP_HOST'],
                microcosm_id=microcosm_id,
                id=group_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(grequests.get(role_url, params=params, headers=headers))
            responses = response_list_to_dict(grequests.map(request.view_requests))
            role = Role.from_api_response(responses[role_url])

            criteria_url, params, headers = RoleCriteriaList.build_request(
                request.META['HTTP_HOST'],
                microcosm_id=microcosm_id,
                id=group_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(grequests.get(criteria_url, params=params, headers=headers))
            responses = response_list_to_dict(grequests.map(request.view_requests))
            criteria = RoleCriteriaList(responses[criteria_url])

            profiles_url, params, headers = RoleProfileList.build_request(
                request.META['HTTP_HOST'],
                microcosm_id=microcosm_id,
                id=group_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(grequests.get(profiles_url, params=params, headers=headers))
            responses = response_list_to_dict(grequests.map(request.view_requests))
            profiles = RoleProfileList(responses[profiles_url])

            view_data = {
                'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
                'site': Site(responses[request.site_url]),
                'site_section': 'memberships',
                'content': microcosm,
                'role': role,
                'criteria': criteria,
                'profiles': profiles,
                'item_type': 'memberships',
                'state_edit': True,
                'pagination': build_pagination_links(responses[microcosm_url]['items']['links'], microcosm.items)
            }

            return render(request, MembershipView.form_template, view_data)
        else:
            return HttpResponseNotAllowed(['GET', 'POST'])




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

        if 'commentPage' in comment.meta.links and\
           'offset' in comment.meta.links['commentPage']['href']:
            offset = comment.meta.links['commentPage']['href'].split('offset=')[1]
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
    @require_http_methods(['GET',])
    def single(request, comment_id):
        """
        Display a single comment.
        """

        url, params, headers = Comment.build_request(request.get_host(), id=comment_id,
            access_token=request.access_token)
        request.view_requests.append(grequests.get(url, params=params, headers=headers))
        responses = response_list_to_dict(grequests.map(request.view_requests))
        content = Comment.from_api_response(responses[url])
        comment_form = CommentForm(
            initial={
            'itemId': content.item_id,
            'itemType': content.item_type,
            'comment_id': content.id,
            }
        )

        # Fetch any attachments on the comment.
        attachments = {}
        c = content.as_dict
        if 'attachments' in c:
            c_attachments = Attachment.retrieve(request.get_host(), "comments", c['id'],
                access_token=request.access_token)
            attachments[str(c['id'])] = c_attachments

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': content,
            'comment_form': comment_form,
            'attachments': attachments
        }

        return render(request, CommentView.single_template, view_data)

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['POST',])
    def create(request):
        """
        Create a comment, processing any attachments (including deletion of attachments) and
        redirecting to the single comment form if there are any validation errors.
        """

        # TODO: determine whether the single comment creation form will use this view.
        # Remove the conditional if not.
        if request.method == 'POST':
            form = CommentForm(request.POST)

            # If invalid, load single comment view showing validation errors.
            if not form.is_valid():
                responses = response_list_to_dict(grequests.map(request.view_requests))
                view_data = {
                    'user': Profile(responses[request.whoami_url], summary=False),
                    'site': Site(responses[request.site_url]),
                    'form': form,
                }
                return render(request, CommentView.form_template, view_data)

            # Create comment with API.
            comment_request = Comment.from_create_form(form.cleaned_data)
            comment = comment_request.create(request.get_host(), access_token=request.access_token)
            try:
                process_attachments(request, comment)
            except ValidationError:
                responses = response_list_to_dict(grequests.map(request.view_requests))
                comment_form = CommentForm(
                    initial={
                    'itemId': comment.item_id,
                    'itemType': comment.item_type,
                    'comment_id': comment.id,
                    'markdown': request.POST['markdown'],
                    }
                )
                view_data = {
                    'user': Profile(responses[request.whoami_url], summary=False),
                    'site': Site(responses[request.site_url]),
                    'content': comment,
                    'comment_form': comment_form,
                    'error': 'Sorry, one of your files was over 5MB. Please try again.',
                }
                return render(request, CommentView.form_template, view_data)

            # API returns which page in the thread this comments appear in, so redirect there.
            if comment.meta.links.get('commentPage'):
                return HttpResponseRedirect(CommentView.build_comment_location(comment))

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET', 'POST',])
    def edit(request, comment_id):
        """
        Edit a comment.
        """

        responses = response_list_to_dict(grequests.map(request.view_requests))
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'site': Site(responses[request.site_url]),
        }

        if request.method == 'POST':
            form = CommentForm(request.POST)
            if form.is_valid():
                comment_request = Comment.from_edit_form(form.cleaned_data)
                comment = comment_request.update(request.get_host(), access_token=request.access_token)

                try:
                    process_attachments(request, comment)
                except ValidationError:
                    responses = response_list_to_dict(grequests.map(request.view_requests))
                    comment_form = CommentForm(
                        initial={
                            'itemId': comment.item_id,
                            'itemType': comment.item_type,
                            'comment_id': comment.id,
                            'markdown': request.POST['markdown'],
                        })
                    view_data = {
                        'user': Profile(responses[request.whoami_url], summary=False),
                        'site': Site(responses[request.site_url]),
                        'content': comment,
                        'comment_form': comment_form,
                        'error': 'Sorry, one of your files was over 5MB. Please try again.',
                    }
                    return render(request, CommentView.form_template, view_data)

                if comment.meta.links.get('commentPage'):
                    return HttpResponseRedirect(CommentView.build_comment_location(comment))
                else:
                    return HttpResponseRedirect(reverse('single-comment', args=(comment.id,)))
            else:
                view_data['form'] = form
                return render(request, CommentView.form_template, view_data)

        if request.method == 'GET':
            comment = Comment.retrieve(request.get_host(), comment_id, access_token=request.access_token)
            view_data['form'] = CommentForm(comment.as_dict)
            return render(request, CommentView.form_template, view_data)

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['POST',])
    def delete(request, comment_id):
        """
        Delete a comment and be redirected to the item.
        """

        comment = Comment.retrieve(request.get_host(), comment_id, access_token=request.access_token)
        comment.delete(request.get_host(), request.access_token)
        if comment.item_type == 'event':
            return HttpResponseRedirect(reverse('single-event', args=(comment.item_id,)))
        elif comment.item_type == 'conversation':
            return HttpResponseRedirect(reverse('single-conversation', args=(comment.item_id,)))
        else:
            return HttpResponseRedirect(reverse('microcosm-list'))

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET',])
    def incontext(request, comment_id):
        """
        Get redirected to the first unread post in a conversation
        """

        response = Comment.incontext(request.get_host(), comment_id, access_token=request.access_token)
        #because redirects are always followed, we can't just get the 'location' value
        response = response['comments']['links']
        for link in response:
            if link['rel'] == 'self':
                response = link['href']
        response = str.replace(str(response), '/api/v1', '')
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
        response = urlunparse((pr[0], pr[1], pr[2], pr[3], queries, frag))
        return HttpResponseRedirect(response)

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET',])
    def source(request, comment_id):
        """
        Retrieve the markdown source for a comment.
        """

        response = Comment.source(request.get_host(), comment_id, request.access_token)
        return HttpResponse(response, content_type='application/json')

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET',])
    def attachments(request, comment_id):
        """
        Retrieve a comment's attachments.
        """

        response = Attachment.source(request.get_host(), type=Comment.api_path_fragment, id=comment_id,
            access_token=request.access_token)
        return HttpResponse(response, content_type='application/json')


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
