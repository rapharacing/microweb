import grequests
import json
import logging

from urllib import urlencode

from urlparse import parse_qs
from urlparse import urlparse
from urlparse import urlunparse

from django.core.urlresolvers import reverse

from django.http import HttpResponseRedirect

from django.shortcuts import render

from django.views.decorators.http import require_http_methods

from core.api.resources import Comment
from core.api.resources import Profile
from core.api.resources import Attachment
from core.api.resources import Site
from core.api.resources import Huddle
from core.api.resources import HuddleList
from core.api.resources import APIException
from core.api.resources import response_list_to_dict

from core.views import ErrorView
from core.views import require_authentication
from core.views import build_pagination_links

from core.forms.forms import CommentForm
from core.forms.forms import HuddleCreate
from core.forms.forms import HuddleEdit

logger = logging.getLogger('huddles.views')

class HuddleView(object):
    create_form = HuddleCreate
    edit_form = HuddleEdit
    form_template = 'forms/huddle.html'
    single_template = 'huddle.html'
    list_template = 'huddles.html'

    @staticmethod
    @require_authentication
    @require_http_methods(['GET',])
    def single(request, huddle_id):

        # Comment offset.
        offset = int(request.GET.get('offset', 0))

        huddle_url, params, headers = Huddle.build_request(request.get_host(), id=huddle_id, offset=offset,
            access_token=request.access_token)
        request.view_requests.append(grequests.get(huddle_url, params=params, headers=headers))
        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException as e:
            if e.status_code == 404:
                return ErrorView.not_found(request)
            elif e.status_code == 403:
                return ErrorView.forbidden(request)
            else:
                return ErrorView.server_error(request)

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
    @require_http_methods(['GET',])
    def list(request):
        # record offset for paging of huddles
        offset = int(request.GET.get('offset', 0))

        huddle_url, params, headers = HuddleList.build_request(request.get_host(), offset=offset,
            access_token=request.access_token)

        request.view_requests.append(grequests.get(huddle_url, params=params, headers=headers))
        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException as e:
            if e.status_code == 404:
                return ErrorView.not_found(request)
            elif e.status_code == 403:
                return ErrorView.forbidden(request)
            else:
                return ErrorView.server_error(request)

        huddles = HuddleList(responses[huddle_url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': huddles,
            'pagination': build_pagination_links(responses[huddle_url]['huddles']['links'], huddles.huddles)
        }
        return render(request, HuddleView.list_template, view_data)


    @staticmethod
    @require_authentication
    @require_http_methods(['GET', 'POST',])
    def create(request):
        """
        Create a huddle.
        """

        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException as e:
            if e.status_code == 404:
                return ErrorView.not_found(request)
            elif e.status_code == 403:
                return ErrorView.forbidden(request)
            else:
                return ErrorView.server_error(request)

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'site': Site(responses[request.site_url]),
        }

        if request.method == 'POST':
            form = HuddleView.create_form(request.POST)
            if form.is_valid():
                hud_request = Huddle.from_create_form(form.cleaned_data)
                try:
                    hud_response = hud_request.create(request.get_host(), request.access_token)
                except APIException as e:
                    if e.status_code == 403:
                        return ErrorView.forbidden(request)
                    else:
                        return ErrorView.server_error(request)

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
                list_of_recipient_ids = request.GET.get('to').split(",")

                for recipient_id in list_of_recipient_ids:
                    try:
                        recipient_profile = Profile.retrieve(request.get_host(), recipient_id)
                    except APIException:
                        # Skip this recipient, but don't return as we may be able to load the others.
                        continue
                    recipients.append({
                        'id': recipient_profile.id,
                        'profileName': recipient_profile.profile_name,
                        'avatar': recipient_profile.avatar
                    })
                view_data['recipients_json'] = json.dumps(recipients)

            view_data['form'] = HuddleView.create_form(initial=dict())
            return render(request, HuddleView.form_template, view_data)

    @staticmethod
    @require_authentication
    @require_http_methods(['POST', ])
    def invite(request, huddle_id):
        """
        Invite participants to a huddle.
        """

        ids = [int(x) for x in request.POST.get('invite_profile_id').split()]
        try:
            Huddle.invite(request.get_host(), huddle_id, ids, request.access_token)
        except APIException as e:
            if e.status_code == 404:
                return ErrorView.not_found(request)
            elif e.status_code == 403:
                return ErrorView.forbidden(request)
            else:
                return ErrorView.server_error(request)

        return HttpResponseRedirect(reverse('single-huddle', args=(huddle_id,)))

    @staticmethod
    @require_authentication
    @require_http_methods(['POST', ])
    def delete(request, huddle_id):
        """
        Delete a huddle and be redirected to the parent microcosm.
        """

        try:
            huddle = Huddle.retrieve(request.get_host(), huddle_id, access_token=request.access_token)
            huddle.delete(request.get_host(), request.access_token)
        except APIException as e:
            if e.status_code == 404:
                return ErrorView.not_found(request)
            elif e.status_code == 403:
                return ErrorView.forbidden(request)
            else:
                return ErrorView.server_error(request)

        return HttpResponseRedirect(reverse('list-huddle'))

    @staticmethod
    @require_authentication
    @require_http_methods(['GET', ])
    def newest(request, huddle_id):
        """
        Get redirected to the first unread post in a huddle
        """

        try:
            response = Huddle.newest(request.get_host(), huddle_id, access_token=request.access_token)
        except APIException as e:
            if e.status_code == 404:
                return ErrorView.not_found(request)
            elif e.status_code == 403:
                return ErrorView.forbidden(request)
            else:
                return ErrorView.server_error(request)

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
