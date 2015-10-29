import grequests
import logging

from urlparse import urlunparse

from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError

from django.http import HttpResponse
from django.http import HttpResponseRedirect

from django.shortcuts import render

from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_safe

from core.api.resources import APIException
from core.api.resources import Attachment
from core.api.resources import Comment
from core.api.resources import COMMENTABLE_ITEM_TYPES
from core.api.resources import Profile
from core.api.resources import RESOURCE_PLURAL
from core.api.resources import response_list_to_dict
from core.api.resources import Site
from core.api.resources import join_path_fragments

from core.forms.forms import CommentForm

from core.views import require_authentication
from core.views import respond_with_error
from core.views import process_attachments
from core.views import build_newest_comment_link

logger = logging.getLogger('comments.views')


create_form = CommentForm
edit_form = CommentForm
form_template = 'forms/create_comment.html'
single_template = 'comment.html'


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


def build_comment_location(comment):
    path = join_path_fragments([RESOURCE_PLURAL[comment.item_type], comment.item_id])

    if 'commentPage' in comment.meta.links and \
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


@require_safe
def single(request, comment_id):
    """
    Display a single comment.
    """

    url, params, headers = Comment.build_request(request.get_host(), id=comment_id,
                                                 access_token=request.access_token)
    request.view_requests.append(grequests.get(url, params=params, headers=headers))
    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
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

    return render(request, single_template, view_data)


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
            try:
                responses = response_list_to_dict(grequests.map(request.view_requests))
            except APIException as exc:
                return respond_with_error(request, exc)
            view_data = {
                'user': Profile(responses[request.whoami_url], summary=False),
                'site': Site(responses[request.site_url]),
                'form': form,
            }
            return render(request, form_template, view_data)

        # Create comment with API.
        comment_request = Comment.from_create_form(form.cleaned_data)
        try:
            comment = comment_request.create(request.get_host(), access_token=request.access_token)
        except APIException as exc:
            return respond_with_error(request, exc)

        try:
            process_attachments(request, comment)
        except ValidationError:
            try:
                responses = response_list_to_dict(grequests.map(request.view_requests))
            except APIException as exc:
                return respond_with_error(request, exc)
            comment_form = CommentForm(
                initial = {
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

        # API returns which page in the thread this comments appear in, so redirect there.
        if comment.meta.links.get('commentPage'):
            return HttpResponseRedirect(build_comment_location(comment))


@require_authentication
@require_http_methods(['GET', 'POST',])
@cache_control(must_revalidate=True, max_age=0)
def edit(request, comment_id):
    """
    Edit a comment.
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
        form = CommentForm(request.POST)
        if form.is_valid():
            comment_request = Comment.from_edit_form(form.cleaned_data)
            try:
                comment = comment_request.update(request.get_host(), access_token=request.access_token)
            except APIException as exc:
                return respond_with_error(request, exc)

            try:
                process_attachments(request, comment)
            except ValidationError:
                try:
                    responses = response_list_to_dict(grequests.map(request.view_requests))
                except APIException as exc:
                    return respond_with_error(request, exc)
                comment_form = CommentForm(
                    initial = {
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
                return render(request, form_template, view_data)

            if comment.meta.links.get('commentPage'):
                return HttpResponseRedirect(build_comment_location(comment))
            else:
                return HttpResponseRedirect(reverse('single-comment', args=(comment.id,)))
        else:
            view_data['form'] = form
            return render(request, form_template, view_data)

    if request.method == 'GET':
        try:
            comment = Comment.retrieve(request.get_host(), comment_id, access_token=request.access_token)
        except APIException as exc:
            return respond_with_error(request, exc)
        view_data['form'] = CommentForm(comment.as_dict)
        return render(request, form_template, view_data)


@require_authentication
@require_http_methods(['POST',])
def delete(request, comment_id):
    """
    Delete a comment and be redirected to the item.
    """

    try:
        comment = Comment.retrieve(request.get_host(), comment_id, access_token=request.access_token)
        comment.delete(request.get_host(), request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)

    if comment.item_type == 'event':
        return HttpResponseRedirect(reverse('single-event', args=(comment.item_id,)))
    elif comment.item_type == 'conversation':
        return HttpResponseRedirect(reverse('single-conversation', args=(comment.item_id,)))
    else:
        return HttpResponseRedirect(reverse('microcosm-list'))


@require_authentication
@require_safe
def incontext(request, comment_id):
    """
    Redirect to the user's first unread comment in a list of comments.
    """

    try:
        response = Comment.incontext(request.get_host(), comment_id, access_token=request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)

    redirect = build_newest_comment_link(response)
    return HttpResponseRedirect(redirect)


@require_authentication
@require_safe
def source(request, comment_id):
    """
    Retrieve the markdown source for a comment.
    """

    try:
        response = Comment.source(request.get_host(), comment_id, request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)
    return HttpResponse(response, content_type='application/json')


@require_authentication
@require_safe
def attachments(request, comment_id):
    """
    Retrieve a comment's attachments.
    """

    try:
        response = Attachment.source(request.get_host(), type=Comment.api_path_fragment, id=comment_id,
            access_token=request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)
    return HttpResponse(response, content_type='application/json')
