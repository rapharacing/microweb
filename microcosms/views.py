import requests
import grequests
import json
import logging

from django.core.urlresolvers import reverse

from django.http import HttpResponseBadRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect

from django.shortcuts import render

from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods

from core.api.resources import Microcosm
from core.api.resources import MicrocosmList
from core.api.resources import Role
from core.api.resources import RoleCriteria
from core.api.resources import RoleCriteriaList
from core.api.resources import RoleList
from core.api.resources import RoleProfile
from core.api.resources import RoleProfileList
from core.api.resources import Profile
from core.api.resources import Site
from core.api.resources import APIException
from core.api.resources import response_list_to_dict

from core.forms.forms import MicrocosmCreate
from core.forms.forms import MicrocosmEdit

from core.views import build_pagination_links
from core.views import require_authentication
from core.views import respond_with_error
from core.views import exception_handler

logger = logging.getLogger('microcosms.views')
microcosm_create_form = MicrocosmCreate
microcosm_edit_form = MicrocosmEdit
microcosm_form_template = 'forms/microcosm.html'
microcosm_single_template = 'microcosm.html'
microcosm_list_template = 'microcosms.html'
members_list_template = 'memberships.html'
members_form_template = 'forms/memberships.html'


@require_http_methods(['GET',])
@cache_control(must_revalidate=True, max_age=0)
def single_microcosm(request, microcosm_id):

    # Pagination offset of items within the microcosm.
    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    microcosm_url, params, headers = Microcosm.build_request(request.get_host(), id=microcosm_id,
                                                             offset=offset, access_token=request.access_token)
    request.view_requests.append(grequests.get(microcosm_url, params=params, headers=headers, timeout=5))
    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)

    microcosm = Microcosm.from_api_response(responses[microcosm_url])

    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
        'site': Site(responses[request.site_url]),
        'content': microcosm,
        'item_type': 'microcosm',
        'pagination': build_pagination_links(responses[microcosm_url]['items']['links'], microcosm.items)
    }

    return render(request, microcosm_single_template, view_data)


@require_http_methods(['GET',])
@cache_control(must_revalidate=True, max_age=0)
def list_microcosms(request):

    # Pagination offset of microcosms.
    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    microcosms_url, params, headers = MicrocosmList.build_request(request.get_host(), offset=offset,
                                                                  access_token=request.access_token)
    request.view_requests.append(grequests.get(microcosms_url, params=params, headers=headers, timeout=5))

    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)

    microcosms = MicrocosmList(responses[microcosms_url])
    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
        'site': Site(responses[request.site_url]),
        'content': microcosms,
        'item_type': 'site',
        'pagination': build_pagination_links(responses[microcosms_url]['microcosms']['links'], microcosms.microcosms)
    }

    return render(request, microcosm_list_template, view_data)


@require_authentication
@require_http_methods(['GET', 'POST',])
@cache_control(must_revalidate=True, max_age=0)
def create_microcosm(request):
    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False),
        'site': Site(responses[request.site_url]),
    }

    if request.method == 'POST':
        form = microcosm_create_form(request.POST)
        if form.is_valid():
            microcosm_request = Microcosm.from_create_form(form.cleaned_data)
            try:
                microcosm_response = microcosm_request.create(request.get_host(), request.access_token)
            except APIException as exc:
                return respond_with_error(request, exc)
            return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm_response.id,)))
        else:
            view_data['form'] = form
            return render(request, microcosm_form_template, view_data)

    if request.method == 'GET':
        view_data['form'] = microcosm_create_form()
        return render(request, microcosm_form_template, view_data)


@require_authentication
@require_http_methods(['GET', 'POST',])
@cache_control(must_revalidate=True, max_age=0)
def edit_microcosm(request, microcosm_id):
    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False),
        'site': Site(responses[request.site_url]),
    }

    if request.method == 'POST':
        form = microcosm_edit_form(request.POST)
        if form.is_valid():
            microcosm_request = Microcosm.from_edit_form(form.cleaned_data)
            try:
                microcosm_response = microcosm_request.update(request.get_host(), request.access_token)
            except APIException as exc:
                return respond_with_error(request, exc)
            return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm_response.id,)))
        else:
            view_data['form'] = form
            return render(request, microcosm_form_template, view_data)

    if request.method == 'GET':
        try:
            microcosm = Microcosm.retrieve(request.get_host(), id=microcosm_id,
                access_token=request.access_token)
        except APIException as exc:
            return respond_with_error(request, exc)
        view_data['form'] = microcosm_edit_form(microcosm.as_dict)
        return render(request, microcosm_form_template, view_data)


@require_authentication
@require_http_methods(['POST',])
def delete_microcosm(request, microcosm_id):
    try:
        microcosm = Microcosm.retrieve(request.get_host(), microcosm_id, access_token=request.access_token)
        microcosm.delete(request.get_host(), request.access_token)
    except APIException as exc:
        return respond_with_error(request, exc)
    return HttpResponseRedirect(reverse(list_microcosms))


@exception_handler
@require_http_methods(['GET',])
@cache_control(must_revalidate=True, max_age=0)
def list_members(request, microcosm_id):
    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    microcosm_url, params, headers = Microcosm.build_request(request.get_host(), id=microcosm_id,
        offset=offset, access_token=request.access_token)
    request.view_requests.append(grequests.get(microcosm_url, params=params, headers=headers, timeout=5))
    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    microcosm = Microcosm.from_api_response(responses[microcosm_url])

    roles_url, params, headers = RoleList.build_request(request.META['HTTP_HOST'], id=microcosm_id,
        offset=offset, access_token=request.access_token)
    request.view_requests.append(grequests.get(roles_url, params=params, headers=headers, timeout=5))
    try:
        responses = response_list_to_dict(grequests.map(request.view_requests))
    except APIException as exc:
        return respond_with_error(request, exc)
    roles = RoleList.from_api_response(responses[roles_url])

    view_data = {
        'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
        'site': Site(responses[request.site_url]),
        'site_section': 'memberships',
        'content': microcosm,
        'memberships': roles,
        'item_type': 'microcosm',
        'pagination': build_pagination_links(responses[roles_url]['roles']['links'], roles.items)
    }

    return render(request, members_list_template, view_data)


@require_authentication
@require_http_methods(['POST',])
def members_api(request, microcosm_id):

    data = json.loads(request.body)
    if data.has_key('deleteRole'):
        # Delete
        roleId = data['deleteRole']

        try:
            response = Role.delete_api(request.get_host(), microcosm_id, roleId, request.access_token)
        except APIException as exc:
            return respond_with_error(request, exc)
        if response.status_code != requests.codes.ok:
            print 'role delete: ' + response.text
            return HttpResponseBadRequest()

        # Need to return a stub here to allow the callee (AJAX) to be happy
        return HttpResponse('{"context": "","status": 200,"data": {}, "error": null}')

    elif data.has_key('role'):
        # Create or update

        role = Role.from_summary(data['role'])
        role.microcosm_id = int(microcosm_id)

        # Create or update the role
        if role.id == 0:
            try:
                response = Role.create_api(request.get_host(), role, request.access_token)
            except APIException as exc:
                return respond_with_error(request, exc)
            if response.status_code != requests.codes.ok:
                print 'role: ' + response.text
                return HttpResponseBadRequest()
            role = Role.from_summary(response.json()['data'])
        else:
            try:
                response = Role.update_api(request.get_host(), role, request.access_token)
            except APIException as exc:
                return respond_with_error(request, exc)
            if response.status_code != requests.codes.found:
                print json.dumps(role.as_dict())
                print 'role: ' + response.text
                return HttpResponseBadRequest()

        # Delete all existing criteria and then add the new ones
        try:
            response = RoleCriteria.delete_all_api(request.get_host(), role.microcosm_id, role.id, request.access_token)
        except APIException as exc:
            return respond_with_error(request, exc)
        if response.status_code != requests.codes.ok:
            print 'role criteria delete all: ' + response.text
            return HttpResponseBadRequest()

        if data.has_key('criteria') and len(data['criteria']) > 0:
            # Loop
            for clob in data['criteria']:
                crit = RoleCriteria.from_summary(clob)

                if crit.id == 0:
                    try:
                        response = RoleCriteria.create_api(request.get_host(), role.microcosm_id, role.id, crit, request.access_token)
                    except APIException as exc:
                        return respond_with_error(request, exc)
                    if response.status_code != requests.codes.ok:
                        print 'role criteria: ' + response.text
                        return HttpResponseBadRequest()
                    crit = RoleCriteria.from_summary(response.json()['data'])
                else:
                    try:
                        response = RoleCriteria.update_api(request.get_host(), role.microcosm_id, role.id, crit, request.access_token)
                    except APIException as exc:
                        return respond_with_error(request, exc)
                    if response.status_code != requests.codes.ok:
                        print 'role criteria: ' + response.text
                        return HttpResponseBadRequest()
                    crit = RoleCriteria.from_summary(response.json()['data'])

        # Delete all existing role profiles and then add the new ones
        try:
            response = RoleProfile.delete_all_api(request.get_host(), role.microcosm_id, role.id, request.access_token)
        except APIException as exc:
            return respond_with_error(request, exc)
        if response.status_code != requests.codes.ok:
            print 'role profile delete all: ' + response.text
            return HttpResponseBadRequest()

        if data.has_key('profiles') and len(data['profiles']) > 0:
            # Loop
            pids = []
            for pid in data['profiles']:
                pids.append({'id': int(pid)})

            try:
                response = RoleProfile.update_api(request.get_host(), role.microcosm_id, role.id, pids, request.access_token)
            except APIException as exc:
                return respond_with_error(request, exc)
            if response.status_code != requests.codes.ok:
                print 'role profiles: ' + response.text
                return HttpResponseBadRequest()

        # Need to return a stub here to allow the callee (AJAX) to be happy
        return HttpResponse('{"context": "","status": 200,"data": {}, "error": null}')
    else:
        return HttpResponseBadRequest()


@require_authentication
@require_http_methods(['GET', 'POST',])
@cache_control(must_revalidate=True, max_age=0)
def create_members(request, microcosm_id):

    if request.method == 'POST':
        pass
    elif request.method == 'GET':
        try:
            offset = int(request.GET.get('offset', 0))
        except ValueError:
            offset = 0

        microcosm_url, params, headers = Microcosm.build_request(request.get_host(), id=microcosm_id,
            offset=offset, access_token=request.access_token)
        request.view_requests.append(grequests.get(microcosm_url, params=params, headers=headers, timeout=5))

        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException as exc:
            return respond_with_error(request, exc)

        microcosm = Microcosm.from_api_response(responses[microcosm_url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'site_section': 'memberships',
            'content': microcosm,
            'item_type': 'memberships',
            'pagination': build_pagination_links(responses[microcosm_url]['items']['links'], microcosm.items)
        }
        return render(request, members_form_template, view_data)


@require_authentication
@require_http_methods(['GET', 'POST',])
@cache_control(must_revalidate=True, max_age=0)
def edit_members(request, microcosm_id, group_id):

    if request.method == 'POST':
        pass
    elif request.method == 'GET':
        try:
            offset = int(request.GET.get('offset', 0))
        except ValueError:
            offset = 0

        microcosm_url, params, headers = Microcosm.build_request(request.get_host(), id=microcosm_id,
            offset=offset, access_token=request.access_token)
        request.view_requests.append(grequests.get(microcosm_url, params=params, headers=headers, timeout=5))

        role_url, params, headers = Role.build_request(request.get_host(), microcosm_id=microcosm_id,
            id=group_id, offset=offset, access_token=request.access_token)
        request.view_requests.append(grequests.get(role_url, params=params, headers=headers, timeout=5))

        criteria_url, params, headers = RoleCriteriaList.build_request(request.get_host(),
            microcosm_id=microcosm_id, id=group_id, offset=offset, access_token=request.access_token)
        request.view_requests.append(grequests.get(criteria_url, params=params, headers=headers, timeout=5))

        profiles_url, params, headers = RoleProfileList.build_request(request.get_host(),
            microcosm_id=microcosm_id, id=group_id, offset=offset, access_token=request.access_token)
        request.view_requests.append(grequests.get(profiles_url, params=params, headers=headers, timeout=5))

        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException as exc:
            return respond_with_error(request, exc)

        microcosm = Microcosm.from_api_response(responses[microcosm_url])
        role = Role.from_api_response(responses[role_url])
        criteria = RoleCriteriaList(responses[criteria_url])
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

        return render(request, members_form_template, view_data)
