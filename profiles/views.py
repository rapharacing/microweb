import grequests
import string
import logging

from django.core.urlresolvers import reverse

from django.http import HttpResponseRedirect

from django.shortcuts import render

from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods

from core.api.resources import FileMetadata
from core.api.resources import Comment
from core.api.resources import Profile
from core.api.resources import Attachment
from core.api.resources import response_list_to_dict
from core.api.resources import ProfileList
from core.api.resources import Search
from core.api.resources import Site
from core.api.exceptions import APIException

from core.forms.forms import ProfileEdit

from core.views import build_pagination_links
from core.views import require_authentication
from core.views import respond_with_error


logger = logging.getLogger('profiles.views')
edit_form = ProfileEdit
form_template = 'forms/profile.html'
single_template = 'profile.html'
list_template = 'profiles.html'


@require_http_methods(['GET',])
@cache_control(must_revalidate=True, max_age=0)
def single(request, profile_id):
    """
    Display a single profile by ID.
    """

    # Fetch profile details.
    profile_url, params, headers = Profile.build_request(request.get_host(), profile_id)
    request.view_requests.append(grequests.get(profile_url, params=params, headers=headers))

    # Fetch items created by this profile.
    search_q = 'type:conversation type:event type:huddle type:comment authorId:%s' % profile_id
    search_params = {'limit': 10, 'q': search_q, 'sort': 'date'}
    search_url, params, headers = Search.build_request(request.get_host(), search_params,
        access_token=request.access_token)
    request.view_requests.append(grequests.get(search_url, params=params, headers=headers))

    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)

    user = Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None
    profile = Profile(responses[profile_url], summary=False)

    view_data = {
        'user': user,
        'content': profile,
        'item_type': 'profile',
        'site': Site(responses[request.site_url]),
        'search': Search.from_api_response(responses[search_url]),
        'site_section': 'people'
    }
    return render(request, single_template, view_data)


@require_http_methods(['GET',])
@cache_control(must_revalidate=True, max_age=0)
def list(request):

    # Record offset for paging of profiles.
    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0
    top = bool(request.GET.get('top', False))
    q = request.GET.get('q', "")
    following = bool(request.GET.get('following', False))
    online = bool(request.GET.get('online', False))

    profiles_url, params, headers = ProfileList.build_request(request.get_host(), offset=offset, top=top,
        q=q, following=following, online=online, access_token=request.access_token)

    request.view_requests.append(grequests.get(profiles_url, params=params, headers=headers))
    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)

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

    return render(request, list_template, view_data)


@require_authentication
@require_http_methods(['GET', 'POST',])
@cache_control(must_revalidate=True, max_age=0)
def edit(request, profile_id):
    """
    Edit a user profile (profile name or avatar).
    """

    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    user = Profile(responses[request.whoami_url], summary=False)
    view_data = {
        'user': user,
        'site': Site(responses[request.site_url]),
    }

    if request.method == 'POST':
        form = edit_form(request.POST)
        if form.is_valid():
            # Upload new avatar if present.
            if request.FILES.has_key('avatar'):
                file_request = FileMetadata.from_create_form(request.FILES['avatar'])
                file_metadata = file_request.create(request.get_host(), request.access_token, 100, 100)
                try:
                    Attachment.create(request.get_host(), file_metadata.file_hash, profile_id=user.id,
                        access_token=request.access_token, file_name=request.FILES['avatar'].name)
                except APIException as exc:
                    return respond_with_error(request, exc)

            # Update the actual profile resource.
            profile_request = Profile(form.cleaned_data)
            profile_response = profile_request.update(request.get_host(), request.access_token)

            # Update or create comment on profile (single comment acts as a bio) if submitted.
            if request.POST.get('markdown'):
                payload = {
                    'itemType': 'profile',
                    'itemId': profile_response.id,
                    'markdown': request.POST.get('markdown'),
                    'inReplyTo': 0
                }

                # If profile already has an attached comment update it, otherwise create a new one.
                if hasattr(profile_response, 'profile_comment'):
                    payload['id'] = profile_response.profile_comment.id
                    if len(request.POST.get('markdown')) < 1:
                        payload['markdown'] = ""
                    comment_request = Comment.from_edit_form(payload)
                    try:
                        comment_request.update(request.get_host(), access_token=request.access_token)
                    except APIException as exc:
                        return respond_with_error(request, exc)
                else:
                    if len(request.POST.get('markdown')) > 0:
                        comment = Comment.from_create_form(payload)
                        try:
                            comment.create(request.get_host(), request.access_token)
                        except APIException as exc:
                            return respond_with_error(request, exc)

            return HttpResponseRedirect(reverse('single-profile', args=(profile_response.id,)))
        else:
            view_data['form'] = form
            return render(request, form_template, view_data)

    if request.method == 'GET':
        try:
            user_profile = Profile.retrieve(request.get_host(), profile_id, request.access_token)
        except APIException as exc:
            return respond_with_error(request, exc)
        view_data['form'] = edit_form(user_profile.as_dict)
        return render(request, form_template, view_data)


@require_authentication
@require_http_methods(['POST',])
def mark_read(request):
    """
    Mark a scope (e.g. site or microcosm) as read for the authenticated user.
    """

    scope = {
        'itemType': request.POST.get('item_type'),
        'itemId': int(request.POST.get('item_id')),
    }
    try:
        Profile.mark_read(request.get_host(), scope, request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)
    return HttpResponseRedirect(request.POST.get('return_path'))
