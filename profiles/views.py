import grequests
import string
import logging

from django.core.urlresolvers import reverse

from django.http import HttpResponseRedirect

from django.shortcuts import render

from django.views.decorators.http import require_http_methods

from microcosm.api.resources import FileMetadata
from microcosm.api.resources import Comment
from microcosm.api.resources import Profile
from microcosm.api.resources import Attachment
from microcosm.api.resources import response_list_to_dict
from microcosm.api.resources import ProfileList
from microcosm.api.resources import Search
from microcosm.api.resources import Site

from microcosm.forms.forms import ProfileEdit

from microcosm.views import exception_handler
from microcosm.views import build_pagination_links

logger = logging.getLogger('microcosm.views')


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
