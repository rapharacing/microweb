import datetime
import grequests
import requests
import json
import logging

from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError

from django.http import HttpResponseRedirect
from django.http import HttpResponseBadRequest
from django.http import HttpResponse

from django.shortcuts import render

from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods

from core.views import respond_with_error
from core.views import require_authentication
from core.views import process_attachments
from core.views import build_pagination_links
from core.views import build_newest_comment_link

from core.api.exceptions import APIException
from core.api.resources import Attachment
from core.api.resources import AttendeeList
from core.api.resources import Comment
from core.api.resources import Event
from core.api.resources import GeoCode
from core.api.resources import Profile
from core.api.resources import response_list_to_dict
from core.api.resources import Site

from core.forms.forms import EventCreate
from core.forms.forms import EventEdit

from core.forms.forms import CommentForm

logger = logging.getLogger('events.views')


create_form = EventCreate
edit_form = EventEdit
form_template = 'forms/event.html'
single_template = 'event.html'
comment_form = CommentForm


@require_http_methods(['GET',])
@cache_control(must_revalidate=True, max_age=0)
def single(request, event_id):
    """
    Display a single event with comments and attendees.
    """

    # Comment offset.
    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    # Create request for event resource.
    event_url, event_params, event_headers = Event.build_request(request.get_host(), id=event_id,
        offset=offset, access_token=request.access_token)
    request.view_requests.append(grequests.get(event_url, params=event_params, headers=event_headers, timeout=5))

    # Create request for event attendees.
    att_url, att_params, att_headers = Event.build_attendees_request(request.get_host(), event_id,
        request.access_token)
    request.view_requests.append(grequests.get(att_url, params=att_params, headers=att_headers, timeout=5))

    # Perform requests and instantiate view objects.
    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    event = Event.from_api_response(responses[event_url])
    comment_form = CommentForm(initial=dict(itemId=event_id, itemType='event'))

    user = Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None

    attendees = AttendeeList(responses[att_url])
    attendees_yes = []
    attendees_invited = []
    user_is_attending = False

    for attendee in attendees.items.items:
        if attendee.rsvp == 'yes':
            attendees_yes.append(attendee)
            if request.whoami_url:
                if attendee.profile.id == user.id:
                    user_is_attending = True
        elif attendee.rsvp == 'maybe':
            attendees_invited.append(attendee)

    # Determine whether the event spans more than one day and if it has expired.
    # TODO: move stuff that is purely rendering to the template.
    today = datetime.datetime.now()
    if hasattr(event, 'when'):
        end_date = event.when + datetime.timedelta(minutes=event.duration)

        is_same_day = False
        if end_date.strftime('%d%m%y') == event.when.strftime('%d%m%y'):
            is_same_day = True

        event_dates = {
            'type': 'multiple' if not is_same_day else 'single',
            'end': end_date
        }

        is_expired = True if int(end_date.strftime('%s')) < int(today.strftime('%s')) else False
    else:
        event_dates = {
            'type': 'tba'
        }
        is_expired = False

    # Why is this a minimum of 10%?
    rsvp_percentage = event.rsvp_percentage
    if len(attendees_yes) and event.rsvp_percentage < 10:
        rsvp_percentage = 10

    # Fetch attachments for all comments on this page.
    # TODO: the code that does this should be in one place.
    attachments = {}
    for comment in event.comments.items:
        c = comment.as_dict
        if 'attachments' in c:
            c_attachments = Attachment.retrieve(request.get_host(), "comments", c['id'],
                access_token=request.access_token)
            attachments[str(c['id'])] = c_attachments

    view_data = {
        'user': user,
        'site': Site(responses[request.site_url]),
        'content': event,
        'comment_form': comment_form,
        'pagination': build_pagination_links(responses[event_url]['comments']['links'], event.comments),
        'item_type': 'event',

        'attendees': attendees,
        'attendees_yes': attendees_yes,
        'attendees_invited': attendees_invited,
        'user_is_attending': user_is_attending,

        'event_dates': event_dates,

        'rsvp_num_attending': len(attendees_yes),
        'rsvp_num_invited': len(attendees_invited),
        'rsvp_percentage': rsvp_percentage,

        'is_expired': is_expired,
        'attachments': attachments
    }

    return render(request, single_template, view_data)


@require_authentication
@require_http_methods(['GET', 'POST',])
@cache_control(must_revalidate=True, max_age=0)
def create(request, microcosm_id):
    """
    Create an event within a microcosm.
    """

    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False),
        'site': Site(responses[request.site_url]),
    }
    user = Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None

    if request.method == 'POST':
        form = create_form(request.POST)
        if form.is_valid():
            event_request = Event.from_create_form(form.cleaned_data)
            try:
                event_response = event_request.create(request.get_host(), request.access_token)
            except APIException as exc:
                return respond_with_error(request, exc)
            # invite attendees
            invites = request.POST.get('invite')
            if len(invites.strip()) > 0:
                invited_list = invites.split(",")
                attendees = []
                if len(invited_list) > 0:
                    for userid in invited_list:
                        if userid != "":
                            attendees.append({
                                'rsvp': 'maybe',
                                'profileId': int(userid)
                            })
                    if len(attendees) > 0:
                        try:
                            response = Event.rsvp_api(request.get_host(), event_response.id, user.id, attendees, access_token=request.access_token)
                        except APIException as exc:
                            return respond_with_error(request, exc)
                        if response.status_code != requests.codes.ok:
                            return HttpResponseBadRequest()

            # create comment
            if request.POST.get('firstcomment') and len(request.POST.get('firstcomment')) > 0:
                payload = {
                    'itemType': 'event',
                    'itemId': event_response.id,
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
                            })
                    view_data = {
                        'user': Profile(responses[request.whoami_url], summary=False),
                        'site': Site(responses[request.site_url]),
                        'content': comment,
                        'comment_form': comment_form,
                        'error': 'Sorry, one of your files was over 5MB. Please try again.',
                        }
                    return render(request, form_template, view_data)

            return HttpResponseRedirect(reverse('single-event', args=(event_response.id,)))

        else:
            print 'Event form is not valid'
            view_data['form'] = form
            view_data['microcosm_id'] = microcosm_id
            return render(request, form_template, view_data)

    if request.method == 'GET':
        view_data['form'] = create_form(initial=dict(microcosmId=microcosm_id))
        view_data['microcosm_id'] = microcosm_id
        return render(request, form_template, view_data)


@require_authentication
@require_http_methods(['GET', 'POST',])
@cache_control(must_revalidate=True, max_age=0)
def edit(request, event_id):
    """
    Edit an event.
    """

    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False),
        'site': Site(responses[request.site_url]),
        'state_edit': True
    }

    if request.method == 'POST':
        form = edit_form(request.POST)
        if form.is_valid():
            event_request = Event.from_edit_form(form.cleaned_data)
            try:
                event_response = event_request.update(request.get_host(), request.access_token)
            except APIException as exc:
                return respond_with_error(request, exc)
            return HttpResponseRedirect(reverse('single-event', args=(event_response.id,)))
        else:
            view_data['form'] = form
            view_data['microcosm_id'] = form['microcosmId']

            return render(request, form_template, view_data)

    if request.method == 'GET':
        try:
            event = Event.retrieve(request.get_host(), id=event_id, access_token=request.access_token)
        except APIException as exc:
            return respond_with_error(request, exc)
        view_data['form'] = edit_form.from_event_instance(event)
        view_data['microcosm_id'] = event.microcosm_id

        try:
            view_data['attendees'] = Event.get_attendees(host=request.get_host(), id=event_id,
                access_token=request.access_token)

            attendees_json = []
            for attendee in view_data['attendees'].items.items:
                attendees_json.append({
                    'id': attendee.profile.id,
                    'profileName': attendee.profile.profile_name,
                    'avatar': attendee.profile.avatar,
                    'sticky': 'true'
                })

            if len(attendees_json) > 0:
                view_data['attendees_json'] = json.dumps(attendees_json)
        except APIException:
            # Missing RSVPs is not critical, but we should know if it doesn't work.
            logger.error(str(APIException))
            pass

        return render(request, form_template, view_data)


@require_authentication
@require_http_methods(['POST',])
def delete(request, event_id):
    """
    Delete an event and be redirected to the parent microcosm.
    """

    event = Event.retrieve(request.get_host(), event_id, access_token=request.access_token)
    try:
        event.delete(request.get_host(), request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)
    return HttpResponseRedirect(reverse('single-microcosm', args=(event.microcosm_id,)))


@require_authentication
@require_http_methods(['GET', ])
@cache_control(must_revalidate=True, max_age=0)
def newest(request, event_id):
    """
    Get redirected to the first unread post in an event.
    """

    try:
        response = Event.newest(request.get_host(), event_id, access_token=request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)

    redirect = build_newest_comment_link(response)
    return HttpResponseRedirect(redirect)


@require_authentication
@require_http_methods(['POST',])
def rsvp(request, event_id):
    """
    Create an attendee (RSVP) for an event. An attendee can be in one of four states:
    invited, yes, maybe, no.
    """
    responses = response_list_to_dict(grequests.map(request.view_requests))
    user = Profile(responses[request.whoami_url], summary=False)

    attendee = [dict(rsvp=request.POST['rsvp'],profileId=user.id),]

    try:
        response = Event.rsvp_api(request.get_host(), event_id, user.id, attendee, access_token=request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)
    if response.status_code != requests.codes.ok:
        return HttpResponseBadRequest() 

    return HttpResponseRedirect(reverse('single-event', args=(event_id,)))


def geocode(request):
    if request.access_token is None:
        raise PermissionDenied
    if request.GET.has_key('q'):
        response = GeoCode.retrieve(request.get_host(), request.GET['q'], request.access_token)
        return HttpResponse(response, content_type='application/json')
    else:
        return HttpResponseBadRequest()