import grequests
import logging

from urllib import urlencode

from urlparse import parse_qs
from urlparse import urlparse
from urlparse import urlunparse

from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError

from django.http import HttpResponse
from django.http import HttpResponseRedirect

from django.shortcuts import render

from django.views.decorators.http import require_http_methods

from microcosm.api.resources import Comment
from microcosm.api.resources import Profile
from microcosm.api.resources import Attachment
from microcosm.api.resources import RESOURCE_PLURAL
from microcosm.api.resources import COMMENTABLE_ITEM_TYPES
from microcosm.api.resources import response_list_to_dict
from microcosm.api.resources import Site

from microcosm.api.resources import join_path_fragments

from microcosm.forms.forms import CommentForm

from microcosm.views import require_authentication
from microcosm.views import exception_handler
from microcosm.views import process_attachments

logger = logging.getLogger('comments.views')

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
