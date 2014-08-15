import logging
import grequests

from django.views.decorators.http import require_http_methods
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render

from core.views import build_pagination_links
from core.views import build_newest_comment_link
from core.views import respond_with_error
from core.views import process_attachments

from core.forms.forms import ConversationCreate
from core.forms.forms import ConversationEdit
from core.forms.forms import CommentForm

from core.api.resources import APIException
from core.api.resources import Attachment
from core.api.resources import Comment
from core.api.resources import Conversation
from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import Site


logger = logging.getLogger('conversations.views')
create_form = ConversationCreate
edit_form = ConversationEdit
form_template = 'forms/conversation.html'
single_template = 'conversation.html'


@require_http_methods(['GET',])
def single(request, conversation_id):

    # Offset of comments.
    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    conversation_url, params, headers = Conversation.build_request(request.get_host(), id=conversation_id,
        offset=offset, access_token=request.access_token)
    request.view_requests.append(grequests.get(conversation_url, params=params, headers=headers))

    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)

    conversation = Conversation.from_api_response(responses[conversation_url])
    comment_form = CommentForm(initial=dict(itemId=conversation_id, itemType='conversation'))

    # get attachments
    attachments = {}
    for comment in conversation.comments.items:
        c = comment.as_dict
        if 'attachments' in c:
            c_attachments = Attachment.retrieve(request.get_host(), "comments", c['id'],
                access_token=request.access_token)
            attachments[str(c['id'])] = c_attachments

    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
        'site': Site(responses[request.site_url]),
        'content': conversation,
        'comment_form': comment_form,
        'pagination': build_pagination_links(responses[conversation_url]['comments']['links'],
            conversation.comments),
        'item_type': 'conversation',
        'attachments': attachments
    }
    return render(request, single_template, view_data)


@require_http_methods(['GET', 'POST',])
def create(request, microcosm_id):
    """
    Create a conversation and first comment in the conversation.
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
            conv_req = Conversation.from_create_form(form.cleaned_data)
            try:
                conv = conv_req.create(request.get_host(), request.access_token)
            except APIException as exc:
                return respond_with_error(request, exc)

            if request.POST.get('firstcomment') and len(request.POST.get('firstcomment')) > 0:
                payload = {
                    'itemType': 'conversation',
                    'itemId': conv.id,
                    'markdown': request.POST.get('firstcomment'),
                    'inReplyTo': 0,
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
                        'error': 'Sorry, one of your files was over 5MB. Please try again.',
                    }
                    return render(request, form_template, view_data)

            return HttpResponseRedirect(reverse('single-conversation', args=(conv.id,)))

        else:
            view_data['form'] = form
            return render(request, form_template, view_data)

    if request.method == 'GET':
        view_data['form'] = create_form(initial=dict(microcosmId=microcosm_id))
        view_data['microcosm_id'] = microcosm_id
        return render(request, form_template, view_data)


@require_http_methods(['GET', 'POST',])
def edit(request, conversation_id):
    """
    Edit a conversation.
    """

    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)

    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False),
        'site': Site(responses[request.site_url]),
        'state_edit': True,
    }

    if request.method == 'POST':
        form = edit_form(request.POST)

        if form.is_valid():
            conv_request = Conversation.from_edit_form(form.cleaned_data)
            try:
                conv_response = conv_request.update(request.get_host(), request.access_token)
            except APIException as exc:
                return respond_with_error(request, exc)
            return HttpResponseRedirect(reverse('single-conversation', args=(conv_response.id,)))
        else:
            view_data['form'] = form
            return render(request, form_template, view_data)

    if request.method == 'GET':
        conversation = Conversation.retrieve(request.get_host(), id=conversation_id,
            access_token=request.access_token)
        view_data['form'] = edit_form.from_conversation_instance(conversation)

        return render(request, form_template, view_data)


@require_http_methods(['POST',])
def delete(request, conversation_id):
    """
    Delete a conversation and be redirected to the parent microcosm.
    """

    conversation = Conversation.retrieve(request.get_host(), conversation_id, access_token=request.access_token)
    try:
        conversation.delete(request.get_host(), request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)
    return HttpResponseRedirect(reverse('single-microcosm', args=(conversation.microcosm_id,)))


@require_http_methods(['GET',])
def newest(request, conversation_id):
    """
    Redirect to the user's first unread post in the conversation.
    """

    try:
        response = Conversation.newest(request.get_host(), conversation_id, access_token=request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)

    redirect = build_newest_comment_link(response)
    return HttpResponseRedirect(redirect)
