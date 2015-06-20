import grequests
import json
import logging

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse

from django.http import HttpResponseRedirect

from django.shortcuts import render

from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_safe

from core.api.resources import APIException
from core.api.resources import Attachment
from core.api.resources import Comment
from core.api.resources import Huddle
from core.api.resources import HuddleList
from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import Site

from core.views import build_newest_comment_link
from core.views import build_pagination_links
from core.views import process_attachments
from core.views import respond_with_error
from core.views import require_authentication

from core.forms.forms import CommentForm
from core.forms.forms import HuddleCreate
from core.forms.forms import HuddleEdit

logger = logging.getLogger('huddles.views')

create_form = HuddleCreate
edit_form = HuddleEdit
form_template = 'forms/huddle.html'
single_template = 'huddle.html'
list_template = 'huddles.html'

@require_authentication
@require_safe
def single(request, huddle_id):

    # Comment offset.
    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    huddle_url, params, headers = Huddle.build_request(request.get_host(), id=huddle_id, offset=offset,
        access_token=request.access_token)
    request.view_requests.append(grequests.get(huddle_url, params=params, headers=headers))
    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)

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

    return render(request, single_template, view_data)


@require_safe
def list(request):
    # Offset for paging of huddles
    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    huddle_url, params, headers = HuddleList.build_request(request.get_host(), offset=offset,
        access_token=request.access_token)

    request.view_requests.append(grequests.get(huddle_url, params=params, headers=headers))
    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)

    huddles = HuddleList(responses[huddle_url])

    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
        'site': Site(responses[request.site_url]),
        'content': huddles,
        'pagination': build_pagination_links(responses[huddle_url]['huddles']['links'], huddles.huddles)
    }
    return render(request, list_template, view_data)


@require_authentication
@require_http_methods(['GET', 'POST',])
@cache_control(must_revalidate=True, max_age=0)
def create(request):
    """
    Create a huddle.
    """

    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)

    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False),
        'site': Site(responses[request.site_url]),
    }

    if request.method == 'POST':
        form = create_form(request.POST)
        if form.is_valid():
            hud_request = Huddle.from_create_form(form.cleaned_data)
            try:
                hud_response = hud_request.create(request.get_host(), request.access_token)
            except APIException as exc:
                return respond_with_error(request, exc)

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
                comment_req = Comment.from_create_form(payload)
                try:
                    comment = comment_req.create(request.get_host(), request.access_token)
                except APIException as exc:
                    return respond_with_error(request, exc)

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
                        'error': 'Sorry, one of your files was over 3MB. Please try again.',
                    }
                    return render(request, form_template, view_data)

            return HttpResponseRedirect(reverse('single-huddle', args=(hud_response.id,)))
        else:
            view_data['form'] = form
            return render(request, form_template, view_data)

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

        view_data['form'] = create_form(initial=dict())
        return render(request, form_template, view_data)


@require_authentication
@require_http_methods(['POST', ])
def invite(request, huddle_id):
    """
    Invite participants to a huddle.
    """

    ids = [int(x) for x in request.POST.get('invite_profile_id').split()]
    try:
        Huddle.invite(request.get_host(), huddle_id, ids, request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)

    return HttpResponseRedirect(reverse('single-huddle', args=(huddle_id,)))


@require_authentication
@require_http_methods(['POST', ])
def delete(request, huddle_id):
    """
    Delete a huddle and be redirected to the parent microcosm.
    """

    try:
        huddle = Huddle.retrieve(request.get_host(), huddle_id, access_token=request.access_token)
        huddle.delete(request.get_host(), request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)

    return HttpResponseRedirect(reverse('list-huddle'))


@require_authentication
@require_safe
def newest(request, huddle_id):
    """
    Get redirected to the first unread post in a huddle
    """

    try:
        response = Huddle.newest(request.get_host(), huddle_id, access_token=request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)

    redirect = build_newest_comment_link(response)
    return HttpResponseRedirect(redirect)
