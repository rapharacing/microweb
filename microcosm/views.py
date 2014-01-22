import requests
import grequests
import string

from functools import wraps

from microweb import settings
from microweb.settings import PAGE_SIZE

from urllib import urlencode

from urlparse import parse_qs
from urlparse import urlparse
from urlparse import urlunparse

from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied


from django.http import Http404
from django.http import HttpResponseNotFound
from django.http import HttpResponseForbidden
from django.http import HttpResponseServerError
from django.http import HttpResponseBadRequest
from django.http import HttpResponse
from django.http import HttpResponseNotAllowed
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
from microcosm.api.resources import UpdateList
from microcosm.api.resources import Update
from microcosm.api.resources import UpdatePreference
from microcosm.api.resources import WatcherList
from microcosm.api.resources import Watcher
from microcosm.api.resources import GeoCode
from microcosm.api.resources import Event
from microcosm.api.resources import AttendeeList
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
from microcosm.api.resources import SearchResult
from microcosm.api.resources import Huddle
from microcosm.api.resources import HuddleList

from microcosm.api.resources import build_url
from microcosm.api.resources import join_path_fragments

from microcosm.forms.forms import EventCreate
from microcosm.forms.forms import EventEdit
from microcosm.forms.forms import MicrocosmCreate
from microcosm.forms.forms import MicrocosmEdit
from microcosm.forms.forms import ConversationCreate
from microcosm.forms.forms import ConversationEdit
from microcosm.forms.forms import CommentForm
from microcosm.forms.forms import ProfileEdit
from microcosm.forms.forms import HuddleCreate
from microcosm.forms.forms import HuddleEdit

import logging
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
			else:
				raise

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
		'page'        : int(paged_list.page),
		'total_pages' : int(paged_list.total_pages),
		'limit'       : int(paged_list.limit),
		'offset'      : int(paged_list.offset)
	}

	for item in request:
		item['href'] = str.replace(str(item['href']),'/api/v1','')
		page_nav[item['rel']] = item

	return page_nav

class ConversationView(object):

	create_form = ConversationCreate
	edit_form = ConversationEdit
	form_template = 'forms/conversation.html'
	single_template = 'conversation.html'

	@staticmethod
	@exception_handler
	def single(request, conversation_id):
		if request.method == 'GET':
			# Offset for paging of event comments
			offset = int(request.GET.get('offset', 0))

			conversation_url, params, headers = Conversation.build_request(
				request.META['HTTP_HOST'],
				id=conversation_id,
				offset=offset,
				access_token=request.access_token
			)
			request.view_requests.append(grequests.get(conversation_url, params=params, headers=headers))
			responses = response_list_to_dict(grequests.map(request.view_requests))
			conversation = Conversation.from_api_response(responses[conversation_url])
			comment_form = CommentForm(
				initial=dict(itemId=conversation_id,itemType='conversation'))

			# get attachments
			attachments = {}
			for comment in conversation.comments.items:
				c = comment.as_dict
				if 'attachments' in c:
					c_attachments = Attachment.retrieve( request.META['HTTP_HOST'], "comments", c['id'], access_token=request.access_token)
					attachments[str(c['id'])] = c_attachments

			view_data = {
				'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
				'site': request.site,
				'content': conversation,
				'comment_form': comment_form,
				'pagination': build_pagination_links(responses[conversation_url]['comments']['links'], conversation.comments),
				'item_type': 'conversation',
				'attachments' : attachments
			}

			return render(request, ConversationView.single_template, view_data)

	@staticmethod
	@exception_handler
	def create(request, microcosm_id):
		"""
		Create a conversation and first comment in the conversation.
		"""

		responses = response_list_to_dict(grequests.map(request.view_requests))
		view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

		if request.method == 'POST':
			form = ConversationView.create_form(request.POST)
			if form.is_valid():
				conv_request = Conversation.from_create_form(form.cleaned_data)
				conv_response = conv_request.create(request.META['HTTP_HOST'], request.access_token)
				if conv_response.id > 0:
					if request.POST.get('firstcomment') and len(request.POST.get('firstcomment')) > 0:

						payload = {
							'itemType'  : 'conversation',
							'itemId'    : conv_response.id,
							'markdown'  : request.POST.get('firstcomment'),
							'inReplyTo' : 0
						}
						comment = Comment.from_create_form(payload)
						comment.create(request.META['HTTP_HOST'], request.access_token)

					return HttpResponseRedirect(reverse('single-conversation', args=(conv_response.id,)))
				else:
					return HttpResponseServerError()
			else:
				view_data['form'] = form
				return render(request, ConversationView.form_template, view_data)

		elif request.method == 'GET':
			view_data['form'] = ConversationView.create_form(initial=dict(microcosmId=microcosm_id))
			view_data['microcosm_id'] = microcosm_id
			return render(request, ConversationView.form_template, view_data)

		else:
			return HttpResponseNotAllowed(['GET', 'POST'])

	@staticmethod
	@exception_handler
	def edit(request, conversation_id):
		"""
		Edit a conversation.
		"""

		responses = response_list_to_dict(grequests.map(request.view_requests))
		view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)
		view_data['state_edit'] = True

		if request.method == 'POST':
			form = ConversationView.edit_form(request.POST)

			if form.is_valid():
				conv_request = Conversation.from_edit_form(form.cleaned_data)
				conv_response = conv_request.update(request.META['HTTP_HOST'], request.access_token)
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
			conversation.delete(request.META['HTTP_HOST'], request.access_token)
			return HttpResponseRedirect(reverse('single-microcosm', args=(conversation.microcosm_id,)))
		else:
			return HttpResponseNotAllowed()

	@staticmethod
	@exception_handler
	def newest(request, conversation_id):
		"""
		Get redirected to the first unread post in a conversation
		"""
		if request.method == 'GET':
			response = Conversation.newest(
				request.META['HTTP_HOST'],
				conversation_id,
				access_token=request.access_token
			)
			# because redirects are always followed, we can't just get the 'location' value
			response = response['comments']['links']
			for link in response:
				if link['rel'] == 'self':
					response = link['href']
			response = str.replace(str(response),'/api/v1','')
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
			response = urlunparse((pr[0],pr[1],pr[2],pr[3],queries,frag))
			return HttpResponseRedirect(response)
		else:
			return HttpResponseNotAllowed()


class HuddleView(object):

	create_form = HuddleCreate
	edit_form = HuddleEdit
	form_template = 'forms/huddle.html'
	single_template = 'huddle.html'
	list_template = 'huddles.html'

	@staticmethod
	@exception_handler
	def single(request, huddle_id):
		if request.method == 'GET':
			# Offset for paging of event comments
			offset = int(request.GET.get('offset', 0))

			huddle_url, params, headers = Huddle.build_request(
				request.META['HTTP_HOST'],
				id=huddle_id,
				offset=offset,
				access_token=request.access_token
			)
			request.view_requests.append(grequests.get(huddle_url, params=params, headers=headers))
			responses = response_list_to_dict(grequests.map(request.view_requests))
			huddle = Huddle.from_api_response(responses[huddle_url])
			comment_form = CommentForm(initial=dict(itemId=huddle_id, itemType='huddle'))

			# get attachments
			attachments = {}
			for comment in huddle.comments.items:
				c = comment.as_dict
				if 'attachments' in c:
					c_attachments = Attachment.retrieve( request.META['HTTP_HOST'], "comments", c['id'], access_token=request.access_token)
					attachments[str(c['id'])] = c_attachments

			#participants json
			import json
			participants_json = [ p.as_dict for p in huddle.participants ]

			view_data = {
				'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
				'site': request.site,
				'content': huddle,
				'comment_form': comment_form,
				'pagination': build_pagination_links(responses[huddle_url]['comments']['links'], huddle.comments),
				'item_type': 'huddle',
				'attachments' : attachments,
				'participants_json' : json.dumps(participants_json)
			}

			return render(request, HuddleView.single_template, view_data)

	@staticmethod
	@exception_handler
	def list(request):

		# record offset for paging of huddles
		offset = int(request.GET.get('offset', 0))

		huddle_url, params, headers = HuddleList.build_request(
			request.META['HTTP_HOST'],
			offset=offset,
			access_token=request.access_token
		)

		request.view_requests.append(grequests.get(huddle_url, params=params, headers=headers))
		responses = response_list_to_dict(grequests.map(request.view_requests))

		huddles = HuddleList(responses[huddle_url])

		view_data = {
			'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
			'site': request.site,
			'content': huddles,
			'pagination': build_pagination_links(responses[huddle_url]['huddles']['links'], huddles.huddles)
		}

		return render(request, HuddleView.list_template, view_data)


	@staticmethod
	@exception_handler
	def create(request):
		"""
		Create a huddle.
		"""

		responses = response_list_to_dict(grequests.map(request.view_requests))
		view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

		if request.method == 'POST':
			form = HuddleView.create_form(request.POST)
			if form.is_valid():
				hud_request = Huddle.from_create_form(form.cleaned_data)
				hud_response = hud_request.create(request.META['HTTP_HOST'], request.access_token)
				if hud_response.id > 0:
					ids = [int(x) for x in request.POST.get('invite').split(',')]
					Huddle.invite(request.META['HTTP_HOST'], hud_response.id, ids, request.access_token)
					if request.POST.get('firstcomment') and len(request.POST.get('firstcomment')) > 0:
						payload = {
							'itemType': 'huddle',
							'itemId': hud_response.id,
							'markdown': request.POST.get('firstcomment'),
							'inReplyTo': 0
						}
						comment = Comment.from_create_form(payload)
						comment.create(request.META['HTTP_HOST'], request.access_token)
					return HttpResponseRedirect(reverse('single-huddle', args=(hud_response.id,)))
			else:
				view_data['form'] = form
				return render(request, HuddleView.form_template, view_data)

		elif request.method == 'GET':

			if request.GET.get('to'):
				recipients = []
				list_of_recipient_ids = request.GET.get('to').split(",");

				for recipient_id in list_of_recipient_ids:
					recipient_profile = Profile.retrieve(request.META['HTTP_HOST'], recipient_id)
					if recipient_profile.id > 0:
						recipients.append({
							'id' 					: recipient_profile.id,
							'profileName' : recipient_profile.profileName,
							'avatar' 			: recipient_profile.avatar
						})

				import json
				view_data['recipients_json'] = json.dumps(recipients)

			view_data['form'] = HuddleView.create_form(initial=dict())
			return render(request, HuddleView.form_template, view_data)

		else:
			return HttpResponseNotAllowed(['GET', 'POST'])


	@staticmethod
	@exception_handler
	def invite(request, huddle_id):
		"""
		Invite participants to a huddle.
		"""

		if request.method == 'POST':
			ids = [int(x) for x in request.POST.get('invite_profile_id').split()]
			Huddle.invite(request.META['HTTP_HOST'], huddle_id, ids, request.access_token)
			return HttpResponseRedirect(reverse('single-huddle', args=(huddle_id,)))

		else:
			return HttpResponseNotAllowed(['POST'])

	@staticmethod
	@exception_handler
	def delete(request, huddle_id):
		"""
		Delete a huddle and be redirected to the parent microcosm.
		"""

		if request.method == 'POST':
			huddle = Huddle.retrieve(
				request.META['HTTP_HOST'],
				huddle_id,
				access_token=request.access_token
			)
			huddle.delete(request.META['HTTP_HOST'], request.access_token)
			return HttpResponseRedirect(reverse('list-huddle'))
		else:
			return HttpResponseNotAllowed()

	@staticmethod
	@exception_handler
	def newest(request, huddle_id):
		"""
		Get redirected to the first unread post in a huddle
		"""
		if request.method == 'GET':
			response = Huddle.newest(
				request.META['HTTP_HOST'],
				huddle_id,
				access_token=request.access_token
			)
			#because redirects are always followed, we can't just get the 'location' value
			response = response['comments']['links']
			for link in response:
				if link['rel'] == 'self':
					response = link['href']
			response = str.replace(str(response),'/api/v1','')
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
			response = urlunparse((pr[0],pr[1],pr[2],pr[3],queries,frag))
			return HttpResponseRedirect(response)
		else:
			return HttpResponseNotAllowed()

class ProfileView(object):

	edit_form = ProfileEdit
	form_template = 'forms/profile.html'
	single_template = 'profile.html'
	list_template = 'profiles.html'

	@staticmethod
	@exception_handler
	def single(request, profile_id):
		"""
		Display a single profile by ID.
		"""

		# Search
		search_url, params, headers = Search.build_request(
			request.META['HTTP_HOST'],
			params = dict(limit=5, q=u'type:microcosm type:conversation type:event type:comment authorId:' + profile_id, sort='date'),
			access_token=request.access_token
		)
		request.view_requests.append(grequests.get(search_url, params=params, headers=headers))
		#responses = response_list_to_dict(grequests.map(request.view_requests))

		# Profile
		responses = response_list_to_dict(grequests.map(request.view_requests))
		view_data = {
			'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
			'item_type': 'profile',
			'site': request.site,
			'search': Search.from_api_response(responses[search_url]),
			'site_section': 'people'
		}

		profile = Profile.retrieve(
			request.META['HTTP_HOST'],
			profile_id,
			request.access_token
		)

		view_data['content'] = profile

		return render(request, ProfileView.single_template, view_data)

	@staticmethod
	@exception_handler
	def list(request):

		# record offset for paging of profiles
		offset = int(request.GET.get('offset', 0))
		top = bool(request.GET.get('top', False))
		q = request.GET.get('q', "")
		following = bool(request.GET.get('following', False))

		profiles_url, params, headers = ProfileList.build_request(
			request.META['HTTP_HOST'],
			offset=offset,
			top=top,
			q=q,
			following=following,
			access_token=request.access_token
		)

		request.view_requests.append(grequests.get(profiles_url, params=params, headers=headers))
		responses = response_list_to_dict(grequests.map(request.view_requests))

		profiles = ProfileList(responses[profiles_url])
		#print responses[profiles_url]['profiles']['links']
		view_data = {
			'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
			'site': request.site,
			'content': profiles,
			'pagination': build_pagination_links(responses[profiles_url]['profiles']['links'], profiles.profiles),
			'q': q,
			'top': top,
			'following': following,
			'alphabet': string.ascii_lowercase,
			'site_section' : 'people'
		}

		return render(request, ProfileView.list_template, view_data)

	@staticmethod
	@exception_handler
	def edit(request, profile_id):
		"""
		Edit a user profile (profile name or avatar).
		"""

		responses = response_list_to_dict(grequests.map(request.view_requests))
		user = Profile(responses[request.whoami_url], summary=False)
		view_data = dict(user=user, site=request.site)

		if request.method == 'POST':
			form = ProfileView.edit_form(request.POST)
			if form.is_valid():
				if request.FILES.has_key('avatar'):
					file_request = FileMetadata.from_create_form(request.FILES['avatar'])

					file_metadata = file_request.create(request.META['HTTP_HOST'], request.access_token, 100, 100)
					Attachment.create(
						request.META['HTTP_HOST'],
						file_metadata.file_hash,
						profile_id=user.id,
						access_token=request.access_token
					)
				profile_request = Profile(form.cleaned_data)
				profile_response = profile_request.update(request.META['HTTP_HOST'], request.access_token)

				if request.POST.get('markdown') and len(request.POST.get('markdown')) > 0:

						payload = {
							'itemType'  : 'profile',
							'itemId'    : profile_response.id,
							'markdown'  : request.POST.get('markdown'),
							'inReplyTo' : 0
						}

						# try to edit comment else create a new one
						try:
							profile_response.profile_comment
							payload['id'] = profile_response.profile_comment.id
							comment_request  = Comment.from_edit_form(payload)
							comment_response = comment_request.update(request.META['HTTP_HOST'], access_token=request.access_token)
						except AttributeError:
							comment = Comment.from_create_form(payload)
							comment.create(request.META['HTTP_HOST'], request.access_token)

				return HttpResponseRedirect(reverse('single-profile', args=(profile_response.id,)))
			else:
				view_data['form'] = form
				return render(request, ProfileView.form_template, view_data)

		elif request.method == 'GET':
			user_profile = Profile.retrieve(
				request.META['HTTP_HOST'],
				profile_id,
				request.access_token
			)

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
		if request.method == 'GET':
			# record offset for paging of items within the microcosm
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

			view_data = {
				'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
				'site': request.site,
				'content': microcosm,
				'item_type': 'microcosm',
				'pagination': build_pagination_links(responses[microcosm_url]['items']['links'], microcosm.items)
			}

			return render(request, MicrocosmView.single_template, view_data)

	@staticmethod
	@exception_handler
	def list(request):

		# record offset for paging of microcosms
		offset = int(request.GET.get('offset', 0))

		microcosms_url, params, headers = MicrocosmList.build_request(
			request.META['HTTP_HOST'],
			offset=offset,
			access_token=request.access_token
		)

		request.view_requests.append(grequests.get(microcosms_url, params=params, headers=headers))
		responses = response_list_to_dict(grequests.map(request.view_requests))

		microcosms = MicrocosmList(responses[microcosms_url])

		view_data = {
			'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
			'site': request.site,
			'content': microcosms,
			'item_type': 'site',
			'pagination': build_pagination_links(responses[microcosms_url]['microcosms']['links'], microcosms.microcosms)
		}

		return render(request, MicrocosmView.list_template, view_data)

	@staticmethod
	@exception_handler
	def create(request):

		responses = response_list_to_dict(grequests.map(request.view_requests))
		view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

		if request.method == 'POST':
			form = MicrocosmView.create_form(request.POST)
			if form.is_valid():
				microcosm_request = Microcosm.from_create_form(form.cleaned_data)
				microcosm_response = microcosm_request.create(request.META['HTTP_HOST'], request.access_token)
				return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm_response.id,)))
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

		responses = response_list_to_dict(grequests.map(request.view_requests))
		view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

		if request.method == 'POST':
			form = MicrocosmView.edit_form(request.POST)
			if form.is_valid():
				microcosm_request = Microcosm.from_edit_form(form.cleaned_data)
				microcosm_response = microcosm_request.update(request.META['HTTP_HOST'], request.access_token)
				return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm_response.id,)))
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
			microcosm = Microcosm.retrieve(request.META['HTTP_HOST'], microcosm_id, access_token=request.access_token)
			microcosm.delete(request.META['HTTP_HOST'], request.access_token)
			return HttpResponseRedirect(reverse(MicrocosmView.list))
		return HttpResponseNotAllowed(['POST'])

	@staticmethod
	@exception_handler
	def create_item_choice(request, microcosm_id):
		"""
		Interstitial page for creating an item (e.g. Event) belonging to a microcosm.
		"""

		microcosm_url, params, headers = Microcosm.build_request(
			request.META['HTTP_HOST'],
			microcosm_id,
			access_token=request.access_token
		)
		request.view_requests.append(grequests.get(microcosm_url, params=params, headers=headers))
		responses = response_list_to_dict(grequests.map(request.view_requests))

		view_data = {
			'user' : Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
			'site' : request.site,
			'content' : Microcosm.from_api_response(responses[microcosm_url])
		}

		return render(request, 'create_item_choice.html', view_data)


class MembershipView(object):

	list_template = 'memberships.html'
	form_template = 'forms/memberships.html'

	@staticmethod
	@exception_handler
	def list(request, microcosm_id):

		if request.method == 'GET':
			# record offset for paging of items within the microcosm
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

			view_data = {
				'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
				'site': request.site,
				'content': microcosm,
				'item_type': 'microcosm',
				'pagination': build_pagination_links(responses[microcosm_url]['items']['links'], microcosm.items)
			}

			return render(request, MembershipView.list_template, view_data)

	@staticmethod
	@exception_handler
	def create(request, microcosm_id):


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
			request.view_requests.append(grequests.get(microcosm_url, params=params, headers=headers))
			responses = response_list_to_dict(grequests.map(request.view_requests))
			microcosm = Microcosm.from_api_response(responses[microcosm_url])

			view_data = {
				'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
				'site': request.site,
				'content': microcosm,
				'item_type': 'microcosm',
				'pagination': build_pagination_links(responses[microcosm_url]['items']['links'], microcosm.items)
			}

			return render(request, MembershipView.form_template, view_data)
		else:
			return HttpResponseNotAllowed(['GET', 'POST'])

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
		if request.method == 'GET':
			# Offset for paging of event comments
			offset = int(request.GET.get('offset', 0))

			event_url, event_params, event_headers = Event.build_request(
				request.META['HTTP_HOST'],
				id           = event_id,
				offset       = offset,
				access_token = request.access_token
			)
			request.view_requests.append(grequests.get(event_url, params=event_params, headers=event_headers))

			att_url, att_params, att_headers = Event.build_attendees_request(
				request.META['HTTP_HOST'],
				event_id,
				request.access_token
			)
			request.view_requests.append(grequests.get(att_url, params=att_params, headers=att_headers))

			responses = response_list_to_dict(grequests.map(request.view_requests))

			event = Event.from_api_response(responses[event_url])
			comment_form = CommentForm(initial=dict(itemId=event_id, itemType='event'))


			user = Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None


			attendees           = AttendeeList(responses[att_url])
			attendees_yes       = []
			attendees_invited   = []
			user_is_attending   = False
			for attendee in attendees.items.items:
				if attendee.rsvp == "yes":
					attendees_yes.append(attendee)

					if user:
						if (attendee.profile.id == user.id):
							user_is_attending = True

				elif attendee.rsvp == "maybe":
					attendees_invited.append(attendee)


			# dates
			import datetime as dt
			today    = dt.datetime.now()
			end_date = event.when + dt.timedelta(minutes=event.duration)

			is_same_day = False
			if (end_date.strftime('%d%m%y') == event.when.strftime('%d%m%y') ):
				is_same_day = True

			event_dates = {
				'type'  : 'multiple' if not is_same_day else 'single',
				'end'   : end_date
			}

			is_expired = True if int(end_date.strftime('%s')) < int(today.strftime('%s')) else False

			#rsvp
			# FIXME: redundant. This code was written before the Event object was modified to include
			# percentage as a default (see resources.py)
			rsvp_limit    = int(responses[event_url]['rsvpLimit'])
			num_attending = len(attendees_yes)
			rsvp_percentage = (num_attending/float(rsvp_limit))*100 if rsvp_limit > 0 else 0

			if (num_attending > 0 and rsvp_percentage < 10):
				rsvp_percentage = 10

			# get attachments
			attachments = {}
			for comment in event.comments.items:
				c = comment.as_dict
				if 'attachments' in c:
					c_attachments = Attachment.retrieve( request.META['HTTP_HOST'], "comments", c['id'], access_token=request.access_token)
					attachments[str(c['id'])] = c_attachments

			view_data = {
				'user'              : user,
				'site'              : request.site,
				'content'           : event,
				'comment_form'      : comment_form,
				'pagination'        : build_pagination_links(responses[event_url]['comments']['links'], event.comments),
				'item_type'         : 'event',

				'attendees'         : attendees,
				'attendees_yes'     : attendees_yes,
				'attendees_invited' : attendees_invited,
				'user_is_attending' : user_is_attending,

				'event_dates'       : event_dates,

				'rsvp_num_attending': num_attending,
				'rsvp_num_invited'  : len(attendees_invited),
				'rsvp_percentage'   : rsvp_percentage,

				'is_expired'        : is_expired,

				'attachments'				: attachments
			}

			return render(request, EventView.single_template, view_data)

	@staticmethod
	@exception_handler
	def create(request, microcosm_id):
		"""
		Create an event within a microcosm.
		"""

		responses = response_list_to_dict(grequests.map(request.view_requests))
		view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)
		user = Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None

		if request.method == 'POST':

			form = EventView.create_form(request.POST)
			if form.is_valid():
				event_request = Event.from_create_form(form.cleaned_data)
				event_response = event_request.create(request.META['HTTP_HOST'], request.access_token)
				if event_response.id > 0:

					# invite attendees
					invites = request.POST.get('invite')
					if len(invites.strip()) > 0:
						invited_list = invites.split(",")
						attendees = []
						if len(invited_list) > 0:
							for userid in invited_list:
								if (userid != ""):
									attendees.append({
										'rsvp' 		: 'maybe',
										'profileId' : int(userid)
									})
							if (len(attendees)>0):
								Event.rsvp(
									request.META['HTTP_HOST'],
									event_response.id,
									user.id,
									attendees,
									access_token=request.access_token
								)

					# create comment
					if request.POST.get('firstcomment') and len(request.POST.get('firstcomment')) > 0:
						payload = {
							'itemType': 'event',
							'itemId': event_response.id,
							'markdown': request.POST.get('firstcomment'),
							'inReplyTo': 0
						}
						comment = Comment.from_create_form(payload)
						comment.create(request.META['HTTP_HOST'], request.access_token)
					return HttpResponseRedirect(reverse('single-event', args=(event_response.id,)))
				else:
					return HttpResponseServerError()
			else:
				view_data['form'] = form
				view_data['microcosm_id'] = microcosm_id
				return render(request, EventView.form_template, view_data)

		elif request.method == 'GET':
			view_data['form'] = EventView.create_form(initial=dict(microcosmId=microcosm_id))
			view_data['microcosm_id'] = microcosm_id
			return render(request, EventView.form_template, view_data)

		else:
			return HttpResponseNotAllowed(['GET', 'POST'])

	@staticmethod
	@exception_handler
	def edit(request, event_id):
		"""
		Edit an event.
		"""

		responses = response_list_to_dict(grequests.map(request.view_requests))
		view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)
		view_data['state_edit'] = True

		if request.method == 'POST':
			form = EventView.edit_form(request.POST)
			if form.is_valid():
				event_request = Event.from_edit_form(form.cleaned_data)
				event_response = event_request.update(request.META['HTTP_HOST'], request.access_token)
				return HttpResponseRedirect(reverse('single-event', args=(event_response.id,)))
			else:
				view_data['form'] = form
				view_data['microcosm_id'] = form['microcosmId']

				return render(request, EventView.form_template, view_data)

		elif request.method == 'GET':
			event = Event.retrieve(request.META['HTTP_HOST'], id=event_id, access_token=request.access_token)
			view_data['form'] = EventView.edit_form.from_event_instance(event)
			view_data['microcosm_id'] = event.microcosm_id

			# fetch attendees
			view_data['attendees'] = Event.get_attendees(host=request.META['HTTP_HOST'], id=event_id, access_token=request.access_token)

			attendees_json = []
			for attendee in view_data['attendees'].items.items:
				attendees_json.append({
					'id' 					: attendee.profile.id,
					'profileName' : attendee.profile.profile_name,
					'avatar' 			: attendee.profile.avatar,
					'sticky'      : 'true'
				})

			if len(attendees_json) > 0:
				import json
				view_data['attendees_json'] = json.dumps(attendees_json)
				print view_data['attendees_json']

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
			event.delete(request.META['HTTP_HOST'], request.access_token)
			return HttpResponseRedirect(reverse('single-microcosm', args=(event.microcosm_id,)))
		else:
			return HttpResponseNotAllowed()

	@staticmethod
	@exception_handler
	def newest(request, event_id):
		"""
		Get redirected to the first unread post in a conversation
		"""
		if request.method == 'GET':
			response = Event.newest(
				request.META['HTTP_HOST'],
				event_id,
				access_token=request.access_token
			)
			# Because redirects are always followed, we can't just use Location.
			response = response['comments']['links']
			for link in response:
				if link['rel'] == 'self':
					response = link['href']
			response = str.replace(str(response),'/api/v1','')
			pr = urlparse(response)
			queries = parse_qs(pr[4])
			frag = ""
			if queries.get('comment_id'):
				frag = 'comment' + queries['comment_id'][0]
				del queries['comment_id']
			# queries is a dictionary of 1-item lists (as we don't re-use keys in our query string).
			# urlencode will encode the lists into the url (offset=[25]) etc. So get the values straight.
			for (key, value) in queries.items():
				queries[key] = value[0]
			queries = urlencode(queries)
			response = urlunparse((pr[0],pr[1],pr[2],pr[3],queries,frag))
			return HttpResponseRedirect(response)
		else:
			return HttpResponseNotAllowed()

	@staticmethod
	def rsvp(request, event_id):
		"""
		Create an attendee (RSVP) for an event. An attendee can be in one of four states:
		invited, confirmed, maybe, no.
		"""
		responses = response_list_to_dict(grequests.map(request.view_requests))
		user = Profile(responses[request.whoami_url], summary=False)

		if request.method == 'POST':
			if user:
				attendee = [{
					'rsvp' : request.POST['rsvp'],
					'profileId' : user.id
				}]
				Event.rsvp(
					request.META['HTTP_HOST'],
					event_id,
					user.id,
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
	def single(request, comment_id):
		"""
		Display a single comment.
		"""

		url, params, headers = Comment.build_request(
			request.META['HTTP_HOST'],
			id=comment_id,
			access_token=request.access_token
		)
		request.view_requests.append(grequests.get(url, params=params, headers=headers))
		responses = response_list_to_dict(grequests.map(request.view_requests))
		content = Comment.from_api_response(responses[url])
		comment_form = CommentForm(
			initial=dict(
				itemId=content.item_id,
				itemType=content.item_type,
				comment_id = content.id
			))

		# get attachments
		attachments = {}
		c = content.as_dict
		if 'attachments' in c:
			c_attachments = Attachment.retrieve( request.META['HTTP_HOST'], "comments", c['id'], access_token=request.access_token)
			attachments[str(c['id'])] = c_attachments

		view_data = {
			'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
			'site': request.site,
			'content': content,
			'comment_form' : comment_form,
			'attachments'  : attachments
		}

		return render(request, CommentView.single_template, view_data)

	@staticmethod
	@exception_handler
	def create(request):
		"""
		Comment forms populate attributes from GET parameters, so require the create
		method to be extended.
		"""

		if not request.access_token:
			raise PermissionDenied

		responses = response_list_to_dict(grequests.map(request.view_requests))
		view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

		if request.method == 'POST':
			form = CommentForm(request.POST)

			if form.is_valid():
				comment_request = Comment.from_create_form(form.cleaned_data)
				comment_response = comment_request.create(request.META['HTTP_HOST'], access_token=request.access_token)

				if comment_response.id > 0:
					if request.FILES.has_key('attachments'):

						for f in request.FILES.getlist('attachments'):
							file_request = FileMetadata.from_create_form(f)
							# File must be under 30KB
							# TODO: use Django's built-in field validators and error messaging
							if len(file_request.file['files']) >= 30720:
								view_data['form'] = form
								view_data['avatar_error'] = 'Sorry, the file you upload must be under 30KB and square.'
								return render(request, CommentView.form_template, view_data)
							else:
								file_metadata = file_request.create(request.META['HTTP_HOST'], request.access_token)
								Attachment.create(
									request.META['HTTP_HOST'],
									file_metadata.file_hash,
									comment_id=comment_response.id,
									access_token=request.access_token
								)

					if comment_response.meta.links.get('commentPage'):
						return HttpResponseRedirect(CommentView.build_comment_location(comment_response))
				else:
					return HttpResponseRedirect(reverse('single-comment', args=(comment_response.id,)))
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

		if not request.access_token:
			raise PermissionDenied

		responses = response_list_to_dict(grequests.map(request.view_requests))
		view_data = dict(user=Profile(responses[request.whoami_url], summary=False), site=request.site)

		if request.method == 'POST':
			form = CommentForm(request.POST)
			if form.is_valid():
				comment_request = Comment.from_edit_form(form.cleaned_data)
				comment_response = comment_request.update(request.META['HTTP_HOST'], access_token=request.access_token)

				# delete attachments if neccessary
				if comment_response.id > 0:
					if request.FILES.has_key('attachments'):

						for f in request.FILES.getlist('attachments'):
							file_request = FileMetadata.from_create_form(f)
							# File must be under 30KB
							# TODO: use Django's built-in field validators and error messaging
							if len(file_request.file['files']) >= 30720:
								view_data['form'] = form
								view_data['avatar_error'] = 'Sorry, the file you upload must be under 30KB and square.'
								return render(request, CommentView.form_template, view_data)
							else:
								file_metadata = file_request.create(request.META['HTTP_HOST'], request.access_token)
								Attachment.create(
									request.META['HTTP_HOST'],
									file_metadata.file_hash,
									comment_id=comment_response.id,
									access_token=request.access_token
								)

					if request.POST.get('attachments-delete'):
						attachments_delete = request.POST.get('attachments-delete').split(",")

						for fileHash in attachments_delete:
							Attachment.delete(
								request.META['HTTP_HOST'],
								Comment.api_path_fragment,
								comment_response.id,
								fileHash
							)

				if comment_response.meta.links.get('commentPage'):
					return HttpResponseRedirect(CommentView.build_comment_location(comment_response))
				else:
					return HttpResponseRedirect(reverse('single-comment', args=(comment_response.id,)))
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
			comment.delete(request.META['HTTP_HOST'], request.access_token)
			if comment.item_type == 'event':
				return HttpResponseRedirect(reverse('single-event', args=(comment.item_id,)))
			elif comment.item_type == 'conversation':
				return HttpResponseRedirect(reverse('single-conversation', args=(comment.item_id,)))
			else:
				return HttpResponseRedirect(reverse('microcosm-list'))
		else:
			return HttpResponseNotAllowed()

	@staticmethod
	@exception_handler
	def incontext(request, comment_id):
		"""
		Get redirected to the first unread post in a conversation
		"""
		if request.method == 'GET':
			response = Comment.incontext(
				request.META['HTTP_HOST'],
				comment_id,
				access_token=request.access_token
			)
			#because redirects are always followed, we can't just get the 'location' value
			response = response['comments']['links']
			for link in response:
				if link['rel'] == 'self':
					response = link['href']
			response = str.replace(str(response),'/api/v1','')
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
			response = urlunparse((pr[0],pr[1],pr[2],pr[3],queries,frag))
			return HttpResponseRedirect(response)
		else:
			return HttpResponseNotAllowed()


	@staticmethod
	@exception_handler
	def source(request, comment_id):
		"""
		Retrieve the markdown source for a comment.
		"""
		if request.access_token is None:
			raise PermissionDenied
		response = Comment.source(
			request.META['HTTP_HOST'],
			comment_id,
			request.access_token
		)
		return HttpResponse(response, content_type='application/json')

	@staticmethod
	@exception_handler
	def attachments(request, comment_id):
		"""
		Retrieve the markdown source for a comment.
		"""
		if request.access_token is None:
			raise PermissionDenied
		response = Attachment.source(
			request.META['HTTP_HOST'],
			type=Comment.api_path_fragment,
			id=comment_id,
			access_token=request.access_token
		)
		return HttpResponse(response, content_type='application/json')

class UpdateView(object):

	list_template = 'updates.html'

	@staticmethod
	@exception_handler
	def list(request):

		view_data = {
			'user': False,
			'site': request.site
		}

		if not request.access_token:
			pass
			# FIXME: need a user friendly error page for unregistered users
			# raise HttpResponseNotAllowed
		else:
			# pagination offset
			offset = int(request.GET.get('offset', 0))

			url, params, headers = UpdateList.build_request(
				request.META['HTTP_HOST'],
				offset=offset,
				access_token=request.access_token
			)
			request.view_requests.append(grequests.get(url, params=params, headers=headers))
			responses = response_list_to_dict(grequests.map(request.view_requests))
			updates_list = UpdateList(responses[url])

			view_data.update({
				'user': Profile(responses[request.whoami_url], summary=False),
				'content': updates_list,
				'pagination': build_pagination_links(responses[url]['updates']['links'], updates_list.updates),
				'site_section' : 'updates'
			})

		return render(request, UpdateView.list_template, view_data)

	@staticmethod
	@exception_handler
	def mark_viewed(request, update_id):
		"""
		Mark a update as viewed by setting a 'viewed' attribute.
		"""

		if request.method == 'POST':
			Update.mark_viewed(request.META['HTTP_HOST'], update_id, request.access_token)
			return HttpResponseRedirect(reverse('list-updates'))
		else:
			return HttpResponseNotAllowed(['POST',])


class WatcherView(object):

	list_template = 'watchers.html'

	@staticmethod
	@exception_handler
	def list(request):

		if not request.access_token:
			raise HttpResponseNotAllowed

		if request.method == 'GET':
			# pagination offset
			offset = int(request.GET.get('offset', 0))

			url, params, headers = WatcherList.build_request(
				request.META['HTTP_HOST'],
				offset=offset,
				access_token=request.access_token
			)
			request.view_requests.append(grequests.get(url, params=params, headers=headers))
			responses = response_list_to_dict(grequests.map(request.view_requests))
			watchers_list = WatcherList(responses[url])

			view_data = {
				'user': Profile(responses[request.whoami_url], summary=False),
				'site': request.site,
				'content': watchers_list,
				'pagination': build_pagination_links(responses[url]['watchers']['links'], watchers_list.watchers)
			}

			return render(request, WatcherView.list_template, view_data)

		if request.method == 'POST':
			if 'watcher_id' in request.POST:
				watchers = request.POST.getlist('watcher_id')
				for w in watchers:
					if request.POST.get('delete_watcher_' + str(w)):
						Watcher.delete(request.META['HTTP_HOST'], w, request.access_token)
					else:
						postdata = {
							'id': int(w),
							'sendEmail': bool(request.POST.get('send_email_'+str(w))),
							'receiveSMS': False,
						}
						Watcher.update(
							request.META['HTTP_HOST'],
							int(w),
							postdata,
							request.access_token
						)
			return HttpResponseRedirect(reverse('list-watchers'))
		else:
			return HttpResponseNotAllowed(['POST',])


	@staticmethod
	@exception_handler
	def single(request):
		if request.method == 'POST':
			postdata = {
				'updateTypeId': 1,
				'itemType': request.POST.get('itemType'),
				'itemId': int(request.POST.get('itemId')),
			}
			if request.POST.get('delete'):
				response = Watcher.delete(
					request.META['HTTP_HOST'],
					postdata,
					request.access_token
				)
				return HttpResponse()
			elif request.POST.get('patch'):
				postdata = {
					'itemType': request.REQUEST.get('itemType'),
					'itemId': int(request.REQUEST.get('itemId')),
					'sendEmail': "true" == request.REQUEST.get('emailMe')
				}
				response = Watcher.update(
					request.META['HTTP_HOST'],
					postdata,
					request.access_token
				)
				if response.status_code == requests.codes.ok:
					return HttpResponse()
				else:
					return HttpResponseBadRequest()
			else:
				responsedata = Watcher.create(
					request.META['HTTP_HOST'],
					postdata,
					request.access_token
				)
				return HttpResponse(responsedata, content_type='application/json')
		else:
			return HttpResponseNotAllowed(['POST','PATCH'])


class UpdatePreferenceView(object):

	list_template = 'forms/update_settings.html'

	@staticmethod
	@exception_handler
	def settings(request):

		if not request.access_token:
			raise HttpResponseNotAllowed

		if request.method == 'GET':

			url, params, headers = UpdatePreference.build_request(
				request.META['HTTP_HOST'],
				request.access_token
			)
			request.view_requests.append(grequests.get(url, params=params, headers=headers))
			url2, params2, headers2 = GlobalOptions.build_request(
				request.META['HTTP_HOST'],
				request.access_token
			)
			request.view_requests.append(grequests.get(url2, params=params2, headers=headers2))
			responses = response_list_to_dict(grequests.map(request.view_requests))
			preference_list = UpdatePreference.from_list(responses[url])
			global_options = GlobalOptions.from_api_response(responses[url2])

			view_data = {
				'user': Profile(responses[request.whoami_url], summary=False),
				'site': request.site,
				'content': preference_list,
				'globaloptions': global_options,
			}
			return render(request, UpdatePreferenceView.list_template, view_data)

		if request.method == 'POST':
			for x in range(1,10):
				if request.POST.get('id_'+str(x)):
					postdata = {
						'id': int(request.POST['id_'+str(x)]),
						'sendEmail': bool(request.POST.get('send_email_'+str(x))),
						'sendSMS': False,
					}
					UpdatePreference.update(
						request.META['HTTP_HOST'],
						request.POST['id_'+str(x)],
						postdata,
						request.access_token
					)

			postdata = {
				'sendEmail': bool(request.POST.get('profile_receive_email')),
				'sendSMS': False,
			}
			GlobalOptions.update(
				request.META['HTTP_HOST'],
				postdata,
				request.access_token
			)
			return HttpResponseRedirect(reverse('updates-settings'))
		else:
			return HttpResponseNotAllowed(['GET'])


class SearchView(object):

	single_template = 'search.html'
	@staticmethod
	@exception_handler
	def single(request):

		if request.method == 'GET':
			# pagination offset
			offset = int(request.GET.get('offset', 0))
			q = request.GET.get('q')

			url, params, headers = Search.build_request(
				request.META['HTTP_HOST'],
				params = request.GET.dict(),
				access_token=request.access_token
			)
			request.view_requests.append(grequests.get(url, params=params, headers=headers))
			responses = response_list_to_dict(grequests.map(request.view_requests))
			search = Search.from_api_response(responses[url])

			view_data = {
				'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
				'site': request.site,
				'content': search,
				'pagination': build_pagination_links(responses[url]['results']['links'], search.results)
			}

			return render(request, SearchView.single_template, view_data)
		else:
			return HttpResponseNotAllowed(['POST',])


class ErrorView(object):

	@staticmethod
	def not_found(request):
		# Only fetch the first element of view_requests (whoami)
		responses = response_list_to_dict(grequests.map(request.view_requests[:1]))
		view_data = {
			'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
			'site': request.site
		}
		context = RequestContext(request, view_data)
		return HttpResponseNotFound(loader.get_template('404.html').render(context))

	@staticmethod
	def forbidden(request):
		view_data = {}
		# If fetching user login data results in HTTP 401, the access token is invalid
		try:
			# Only fetch the first element of view_requests (whoami)
			responses = response_list_to_dict(grequests.map(request.view_requests[:1]))
			view_data['user'] = Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None
		except APIException as e:
			if e.status_code == 401 or e.status_code == 403:
				view_data['logout'] = True
		view_data['site'] = request.site
		context = RequestContext(request, view_data)
		response = HttpResponseForbidden(loader.get_template('403.html').render(context))
		if view_data.get('logout'):
			response.delete_cookie('access_token')
		return response

	@staticmethod
	def server_error(request):
		# Only fetch the first element of view_requests (whoami)
		responses = response_list_to_dict(grequests.map(request.view_requests[:1]))
		view_data = {
			'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
			'site': request.site,
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

		url = build_url(request.META['HTTP_HOST'], ['auth'])
		response = requests.post(url, data=data, headers={})
		access_token = response.json()['data']

		response = HttpResponseRedirect(target_url if target_url != '' else '/')
		response.set_cookie('access_token', access_token, httponly=True)
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

		view_data = dict(site=request.site)
		#response = render(request, 'logout.html', view_data)
		response = redirect('/')

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


class FaviconView(RedirectView):

	def get_redirect_url(self, **kwargs):
		return settings.STATIC_URL + 'img/favico.png'


class RobotsView(TemplateView):

	template_name = 'robots.txt'
	content_type = 'text/plain'

	def get_context_data(self, **kwargs):
		return super(RobotsView, self).get_context_data(**kwargs)
