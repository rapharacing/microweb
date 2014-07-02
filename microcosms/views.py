import requests
import grequests
import json
import logging

from django.core.urlresolvers import reverse

from django.http import HttpResponseBadRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import HttpResponseNotAllowed

from django.shortcuts import render

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

from core.views import ErrorView
from core.views import build_pagination_links
from core.views import require_authentication
from core.views import exception_handler

logger = logging.getLogger('microcosms.views')


class MicrocosmView(object):
    create_form = MicrocosmCreate
    edit_form = MicrocosmEdit
    form_template = 'forms/microcosm.html'
    single_template = 'microcosm.html'
    list_template = 'microcosms.html'

    @staticmethod
    @require_http_methods(['GET',])
    def single(request, microcosm_id):

        # Pagination offset of items within the microcosm.
        offset = int(request.GET.get('offset', 0))

        microcosm_url, params, headers = Microcosm.build_request(request.get_host(), id=microcosm_id,
                                                                 offset=offset, access_token=request.access_token)
        request.view_requests.append(grequests.get(microcosm_url, params=params, headers=headers))
        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException as e:
            if e.status_code == 403:
                return ErrorView.forbidden(request)
            elif e.status_code == 404:
                return ErrorView.not_found(request)
            else:
                return ErrorView.server_error(request)

        microcosm = Microcosm.from_api_response(responses[microcosm_url])

        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': microcosm,
            'item_type': 'microcosm',
            'pagination': build_pagination_links(responses[microcosm_url]['items']['links'], microcosm.items)
        }

        return render(request, MicrocosmView.single_template, view_data)

    @staticmethod
    @require_http_methods(['GET',])
    def list(request):

        # Pagination offset of microcosms.
        offset = int(request.GET.get('offset', 0))

        microcosms_url, params, headers = MicrocosmList.build_request(request.get_host(), offset=offset,
                                                                      access_token=request.access_token)
        request.view_requests.append(grequests.get(microcosms_url, params=params, headers=headers))

        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException as e:
            if e.status_code == 403:
                return ErrorView.forbidden(request)
            elif e.status_code == 404:
                return ErrorView.not_found(request)
            else:
                return ErrorView.server_error(request)

        microcosms = MicrocosmList(responses[microcosms_url])
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'content': microcosms,
            'item_type': 'site',
            'pagination': build_pagination_links(responses[microcosms_url]['microcosms']['links'], microcosms.microcosms)
        }

        return render(request, MicrocosmView.list_template, view_data)

    @staticmethod
    @require_authentication
    @require_http_methods(['GET', 'POST',])
    def create(request):
        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException:
            return ErrorView.server_error(request)
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'site': Site(responses[request.site_url]),
        }

        if request.method == 'POST':
            form = MicrocosmView.create_form(request.POST)
            if form.is_valid():
                microcosm_request = Microcosm.from_create_form(form.cleaned_data)
                try:
                    microcosm_response = microcosm_request.create(request.get_host(), request.access_token)
                except APIException as e:
                    if e.status_code == 403:
                        return ErrorView.forbidden(request)
                    else:
                        return ErrorView.server_error(request)
                return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm_response.id,)))
            else:
                view_data['form'] = form
                return render(request, MicrocosmView.form_template, view_data)

        if request.method == 'GET':
            view_data['form'] = MicrocosmView.create_form()
            return render(request, MicrocosmView.form_template, view_data)


    @staticmethod
    @require_authentication
    @require_http_methods(['GET', 'POST',])
    def edit(request, microcosm_id):
        try:
            responses = response_list_to_dict(grequests.map(request.view_requests))
        except APIException as e:
            if e.status_code == 403:
                return ErrorView.forbidden(request)
            elif e.status_code == 404:
                return ErrorView.not_found(request)
            else:
                return ErrorView.server_error(request)
        view_data = {
            'user': Profile(responses[request.whoami_url], summary=False),
            'site': Site(responses[request.site_url]),
        }

        if request.method == 'POST':
            form = MicrocosmView.edit_form(request.POST)
            if form.is_valid():
                microcosm_request = Microcosm.from_edit_form(form.cleaned_data)
                try:
                    microcosm_response = microcosm_request.update(request.get_host(), request.access_token)
                except APIException as e:
                    if e.status_code == 403:
                        return ErrorView.forbidden(request)
                    elif e.status_code == 404:
                        return ErrorView.not_found(request)
                    else:
                        return ErrorView.server_error(request)
                return HttpResponseRedirect(reverse('single-microcosm', args=(microcosm_response.id,)))
            else:
                view_data['form'] = form
                return render(request, MicrocosmView.form_template, view_data)

        if request.method == 'GET':
            try:
                microcosm = Microcosm.retrieve(request.get_host(), id=microcosm_id, access_token=request.access_token)
            except APIException as e:
                if e.status_code == 403:
                    return ErrorView.forbidden(request)
                elif e.status_code == 404:
                    return ErrorView.not_found(request)
                else:
                    return ErrorView.server_error(request)
            view_data['form'] = MicrocosmView.edit_form(microcosm.as_dict)
            return render(request, MicrocosmView.form_template, view_data)

    @staticmethod
    @require_authentication
    @require_http_methods(['POST',])
    def delete(request, microcosm_id):
        try:
            microcosm = Microcosm.retrieve(request.get_host(), microcosm_id, access_token=request.access_token)
            microcosm.delete(request.get_host(), request.access_token)
        except APIException as e:
            if e.status_code == 403:
                return ErrorView.forbidden(request)
            elif e.status_code == 404:
                return ErrorView.not_found(request)
            else:
                return ErrorView.server_error(request)
        return HttpResponseRedirect(reverse(MicrocosmView.list))


class MembershipView(object):
    list_template = 'memberships.html'
    form_template = 'forms/memberships.html'

    @staticmethod
    @exception_handler
    @require_http_methods(['GET',])
    def list(request, microcosm_id):
        offset = int(request.GET.get('offset', 0))

        microcosm_url, params, headers = Microcosm.build_request(
            request.get_host(),
            id=microcosm_id,
            offset=offset,
            access_token=request.access_token
        )
        request.view_requests.append(
            grequests.get(microcosm_url, params=params, headers=headers)
        )
        responses = response_list_to_dict(grequests.map(request.view_requests))
        microcosm = Microcosm.from_api_response(responses[microcosm_url])

        roles_url, params, headers = RoleList.build_request(
            request.META['HTTP_HOST'],
            id=microcosm_id,
            offset=offset,
            access_token=request.access_token
        )
        request.view_requests.append(
            grequests.get(roles_url, params=params, headers=headers)
        )
        responses = response_list_to_dict(grequests.map(request.view_requests))
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

        return render(request, MembershipView.list_template, view_data)

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['POST',])
    def api(request, microcosm_id):

        data = json.loads(request.body)

        if data.has_key('deleteRole'):
            # Delete
            roleId = data['deleteRole']

            response = Role.delete_api(request.get_host(), microcosm_id, roleId, request.access_token)
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
                response = Role.create_api(request.get_host(), role, request.access_token)
                if response.status_code != requests.codes.ok:
                    print 'role: ' + response.text
                    return HttpResponseBadRequest()
                role = Role.from_summary(response.json()['data'])
            else:
                response = Role.update_api(request.get_host(), role, request.access_token)
                if response.status_code != requests.codes.found:
                    print json.dumps(role.as_dict())
                    print 'role: ' + response.text
                    return HttpResponseBadRequest()

            # Delete all existing criteria and then add the new ones
            response = RoleCriteria.delete_all_api(request.get_host(), role.microcosm_id, role.id, request.access_token)
            if response.status_code != requests.codes.ok:
                print 'role criteria delete all: ' + response.text
                return HttpResponseBadRequest()

            if data.has_key('criteria') and len(data['criteria']) > 0:
                # Loop
                for clob in data['criteria']:
                    crit = RoleCriteria.from_summary(clob)

                    if crit.id == 0:
                        response = RoleCriteria.create_api(request.get_host(), role.microcosm_id, role.id, crit, request.access_token)
                        if response.status_code != requests.codes.ok:
                            print 'role criteria: ' + response.text
                            return HttpResponseBadRequest()
                        crit = RoleCriteria.from_summary(response.json()['data'])
                    else:
                        response = RoleCriteria.update_api(request.get_host(), role.microcosm_id, role.id, crit, request.access_token)
                        if response.status_code != requests.codes.ok:
                            print 'role criteria: ' + response.text
                            return HttpResponseBadRequest()
                        crit = RoleCriteria.from_summary(response.json()['data'])

            # Delete all existing role profiles and then add the new ones
            response = RoleProfile.delete_all_api(request.get_host(), role.microcosm_id, role.id, request.access_token)
            if response.status_code != requests.codes.ok:
                print 'role profile delete all: ' + response.text
                return HttpResponseBadRequest()

            if data.has_key('profiles') and len(data['profiles']) > 0:
                # Loop
                pids = []
                for pid in data['profiles']:
                    pids.append({'id': int(pid)})

                response = RoleProfile.update_api(request.get_host(), role.microcosm_id, role.id, pids, request.access_token)
                if response.status_code != requests.codes.ok:
                    print 'role profiles: ' + response.text
                    return HttpResponseBadRequest()

            # Need to return a stub here to allow the callee (AJAX) to be happy
            return HttpResponse('{"context": "","status": 200,"data": {}, "error": null}')
        else:
            return HttpResponseBadRequest()

    @staticmethod
    @exception_handler
    @require_authentication
    @require_http_methods(['GET', 'POST',])
    def create(request, microcosm_id):
        if request.method == 'POST':
            pass
        elif request.method == 'GET':
            offset = int(request.GET.get('offset', 0))

            microcosm_url, params, headers = Microcosm.build_request(
                request.get_host(),
                id=microcosm_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(
                grequests.get(microcosm_url, params=params, headers=headers)
            )
            responses = response_list_to_dict(grequests.map(request.view_requests))
            microcosm = Microcosm.from_api_response(responses[microcosm_url])

            roles_url, params, headers = RoleList.build_request(
                request.META['HTTP_HOST'],
                id=microcosm_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(
                grequests.get(roles_url, params=params, headers=headers)
            )
            responses = response_list_to_dict(grequests.map(request.view_requests))
            roles = RoleList.from_api_response(responses[roles_url])

            view_data = {
            'user': Profile(responses[request.whoami_url], summary=False) if request.whoami_url else None,
            'site': Site(responses[request.site_url]),
            'site_section': 'memberships',
            'content': microcosm,
            'item_type': 'memberships',
            'pagination': build_pagination_links(responses[microcosm_url]['items']['links'], microcosm.items)
            }

            return render(request, MembershipView.form_template, view_data)

    @staticmethod
    @exception_handler
    def edit(request, microcosm_id, group_id):

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
            responses = response_list_to_dict(grequests.map(request.view_requests))
            microcosm = Microcosm.from_api_response(responses[microcosm_url])

            role_url, params, headers = Role.build_request(
                request.META['HTTP_HOST'],
                microcosm_id=microcosm_id,
                id=group_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(grequests.get(role_url, params=params, headers=headers))
            responses = response_list_to_dict(grequests.map(request.view_requests))
            role = Role.from_api_response(responses[role_url])

            criteria_url, params, headers = RoleCriteriaList.build_request(
                request.META['HTTP_HOST'],
                microcosm_id=microcosm_id,
                id=group_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(grequests.get(criteria_url, params=params, headers=headers))
            responses = response_list_to_dict(grequests.map(request.view_requests))
            criteria = RoleCriteriaList(responses[criteria_url])

            profiles_url, params, headers = RoleProfileList.build_request(
                request.META['HTTP_HOST'],
                microcosm_id=microcosm_id,
                id=group_id,
                offset=offset,
                access_token=request.access_token
            )
            request.view_requests.append(grequests.get(profiles_url, params=params, headers=headers))
            responses = response_list_to_dict(grequests.map(request.view_requests))
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

            return render(request, MembershipView.form_template, view_data)
        else:
            return HttpResponseNotAllowed(['GET', 'POST'])


