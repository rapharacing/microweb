import json

import requests
from requests import RequestException

from dateutil.parser import parse as parse_timestamp

from microcosm.api.exceptions import APIException
from microweb.helpers import DateTimeEncoder
from microweb.helpers import build_url

# Item types that can have comments
COMMENTABLE_ITEM_TYPES = [
    'event',
    'conversation',
    'poll'
]


class APIResource(object):
    """
    Base API resource that performs HTTP operations. Each API class should subclass this
    to deal with custom validation and JSON processing.
    """

    @classmethod
    def retrieve(cls, host, id=None, offset=None, access_token=None, url_override=None):
        """
        GET an API resource. If resource ID is omitted, returns a list. Appends access_token
        and offset (for paging) if provided.
        """

        headers = {'Host': host}

        if url_override:
            resource_url = url_override
        else:
            path_fragments = [cls.resource_fragment]
            if id: path_fragments.append(id)
            resource_url = build_url(host, path_fragments)

        params = {}
        if access_token: params['access_token'] = access_token
        if offset: params['offset'] = offset

        response = requests.get(resource_url, params=params, headers=headers)

        try:
            resource = response.json()
        except ValueError:
            raise APIException('Response not valid json: %s' % response.content, 500)

        if resource['error']:
            raise APIException(resource['error'], response.status_code)

        if not resource['data']:
            raise APIException('No data returned at: %s' % resource_url)

        return resource['data']

    @classmethod
    def create(cls, host, data, access_token, headers=None):
        """
        Create an API resource with POST.
        """

        resource_url = build_url(host, [cls.resource_fragment])
        params = {'access_token': access_token}

        if headers:
            headers['Content-Type'] = 'application/json'
            headers['Host'] = host
        else:
            headers = {
                'Content-Type': 'application/json',
                'Host': host
            }

        response = requests.post(
            resource_url,
            data=json.dumps(data, cls=DateTimeEncoder),
            headers=headers,
            params=params
        )

        try:
            resource = response.json()
        except ValueError:
            raise APIException('Response not valid json: %s' % response.content, 500)

        if resource['error']:
            raise APIException(resource['error'], response.status_code)

        if not resource['data']:
            raise APIException('No data returned at: %s' % resource_url)

        return resource['data']

    @classmethod
    def update(cls, host, data, id, access_token):
        """
        Update an API resource with PUT.
        """

        resource_url = build_url(host, [cls.resource_fragment, id])

        headers = {
            'Content-Type': 'application/json',
            'Host': host,
        }
        params = {
            'method': 'PUT',
            'access_token': access_token,
        }

        response = requests.post(
            resource_url,
            data=json.dumps(data, cls=DateTimeEncoder),
            headers=headers,
            params=params
        )

        try:
            resource = response.json()
        except ValueError:
            raise APIException('The API has returned invalid json: %s' % response.content, 500)

        if resource['error']:
            raise APIException(resource['error'], response.status_code)

        if not resource['data']:
            raise APIException('No data returned at: %s' % resource_url)

        return resource['data']

    @classmethod
    def delete(cls, host, id, access_token):
        """
        DELETE an API resource. ID must be supplied.

        A 'data' object is never returned by a DELETE, so this
        method will raise an exception on failure. In normal
        operation the method simply returns.
        """

        path_fragments = [cls.resource_fragment]

        if id:
            path_fragments.append(id)
        elif access_token:
            path_fragments.append(access_token)
        else:
            raise AssertionError, 'You must supply either an id or '\
                                  'an access_token to delete'

        resource_url = build_url(host, path_fragments)
        params = {
            'method': 'DELETE',
            'access_token': access_token,
        }
        headers = {'Host': host}
        response = requests.post(resource_url, params=params, headers=headers)

        try:
            resource = response.json()
        except ValueError:
            raise APIException('The API has returned invalid json: %s' % response.content, 500)

        if resource['error']:
            raise APIException(resource['error'], response.status_code)


class Site(APIResource):
    """
    Represents the current site (title, logo, etc.).
    """

    resource_fragment = 'site'

    @classmethod
    def retrieve(cls, host):
        resource = super(Site, cls).retrieve(host)
        return Site(resource)

    def __init__(self, data):
        self.site_id = data['siteId']
        self.title = data['title']
        self.description = data['description']
        self.subdomain_key = data['subdomainKey']
        self.domain = data['domain']
        self.owned_by = Profile(data['ownedBy'])
        self.logo_url = data['logo_url']


class User(APIResource):
    item_type = 'user'
    resource_fragment = 'users'

    @classmethod
    def retrieve(cls, host, id, access_token):
        resource = super(User, cls).retrieve(host, id=id, access_token=access_token)
        return User(resource)

    # Currently only 'email is used on User objects
    def __init__(self, data):
        self.email_address = data['email']


class Authentication(APIResource):
    resource_fragment = 'auth'


class WhoAmI(APIResource):
    item_type = 'whoami'
    resource_fragment = 'whoami'

    @classmethod
    def retrieve(cls, host, access_token):
        resource = super(WhoAmI, cls).retrieve(host, access_token=access_token)
        return Profile(resource)


class Profile(APIResource):
    item_type = 'profile'
    resource_fragment = 'profiles'

    @classmethod
    def retrieve(cls, host, id, access_token=None):
        resource = super(Profile, cls).retrieve(host, id, access_token=access_token)
        return Profile(resource)

    def __init__(self, data, summary=True):
        self.id = data['id']
        self.site_id = data['siteId']
        self.user_id = data['userId']
        self.profile_name = data['profileName']
        self.visible = data['visible']
        self.gravatar = data['gravatar']
        self.meta = Meta(data['meta'])

        if not summary:
            self.style_id = data['styleId']
            self.item_count = data['itemCount']
            self.comment_count = data['commentCount']
            self.created = parse_timestamp(data['created'])
            self.last_active = parse_timestamp(data['lastActive'])
            self.banned = data['banned']
            self.admin = data['admin']


class Microcosm(APIResource):
    """
    Represents a single microcosm, containing items (conversations, events, ...)
    """

    resource_fragment = 'microcosms'

    @classmethod
    def retrieve(cls, host, id, offset=None, access_token=None):
        resource = super(Microcosm, cls).retrieve(host, id, offset, access_token)
        return Microcosm(resource, summary=False)

    def __init__(self, data, summary=True):
        self.id = data['id']
        self.site_id = data['siteId']
        self.visibility = data['visibility']
        self.title = data['title']
        self.description = data['description']
        self.moderators = data['moderators']
        self.meta = Meta(data['meta'])

        if summary:
            if data.has_key('mostRecentUpdate') \
            and data['mostRecentUpdate'] is not None:
                self.most_recent_update = Item(data['mostRecentUpdate'])
            self.total_items = data['totalItems']
            self.total_comments = data['totalComments']
        else:
            self.items = PaginatedList(data['items'], Item)


class MicrocosmList(APIResource):
    """
    Represents a list of microcosms for a given site.
    """

    resource_fragment = 'microcosms'

    @classmethod
    def retrieve(cls, host, offset=None, access_token=None):
        resource = super(MicrocosmList, cls).retrieve(host, offset=offset, access_token=access_token)
        return MicrocosmList(resource)

    def __init__(self, data):
        self.microcosms = PaginatedList(data['microcosms'], Microcosm)
        self.meta = Meta(data['meta'])


class Item():

    """
    Represents an item contained within a microcosm. Only used when
    fetching a single microcosm to represent the list of items
    contained within.
    """

    def __init__(self, data):
        self.id = data['id']
        self.item_type = data['itemType']
        self.microcosm_id = data['microcosmId']
        self.title = data['title']
        self.total_comments = data['totalComments']
        self.total_views = data['totalViews']
        self.last_comment_id = data['lastCommentId']
        self.last_comment_created_by = Profile(data['lastCommentCreatedBy'])
        self.last_comment_created = parse_timestamp(data['lastCommentCreated'])
        self.meta = Meta(data['meta'])


class PaginatedList():

    """
    Generic list of items and pagination metadata (total, number of pages, etc.).
    """

    def __init__(self, list, list_item_cls):
        self.total = list['total']
        self.limit = list['limit']
        self.offset = list['offset']
        self.max_offset = list['maxOffset']
        self.total_pages = list['totalPages']
        self.page = list['page']
        self.type = list['type']
        self.items = [list_item_cls(item) for item in list['items']]


class Meta():

    """
    Represents a resource 'meta' type, including creation time/user,
    flags, links, and permissions.
    """

    def __init__(self, data):
        if data.has_key('created'): self.created = (data['created'])
        if data.has_key('createdBy'): self.created_by = Profile(data['createdBy'])
        if data.has_key('edited'): self.created = (data['edited'])
        if data.has_key('editedBy'): self.created_by = Profile(data['editedBy'])
        if data.has_key('flags'): self.flags = data['flags']
        if data.has_key('links'): self.links = data['links']
        if data.has_key('permissions'): self.permissions = PermissionSet(data['permissions'])


class PermissionSet():

    """
    Represents user permissions on a resource.
    """

    def __init__(self, data):
        self.create = data['create']
        self.read = data['read']
        self.update = data['update']
        self.delete = data['delete']
        self.guest = data['guest']
        self.super_user = data['superUser']


class Conversation(APIResource):
    """
    Represents a conversation (title and list of comments).
    """

    resource_fragment = 'conversations'

    @classmethod
    def retrieve(cls, host, id=None, offset=None, access_token=None):
        resource = super(Conversation, cls).retrieve(host, id, offset, access_token)
        return APIResource.process_timestamp(resource)

    def __init__(self, data):
        self.id = data['id']
        self.microcosm_id = data['microcosmId']
        self.title = data['title']
        self.meta = Meta(data['meta'])
        self.comments = PaginatedList(data['comments'], None)


class Event(APIResource):
    """
    Represents an event (event details and list of comments).
    """

    resource_fragment = 'events'

    @classmethod
    def retrieve(cls, host, id=None, offset=None, access_token=None):
        resource = super(Event, cls).retrieve(host, id, offset, access_token)
        return APIResource.process_timestamp(resource)

    @classmethod
    def retrieve_attendees(cls, host, id, access_token=None):
        """
        Retrieve a list of attendees for an event.
        TODO: pagination support
        """

        resource_url = build_url(host, [cls.resource_fragment, id, 'attendees'])
        resource = APIResource.retrieve(host, id=id, access_token=access_token, url_override=resource_url)
        resource = cls.create_linkmap(resource)
        return APIResource.process_timestamp(resource)

    @classmethod
    def rsvp(cls, host, event_id, profile_id, attendance_data, access_token):
        """
        Create or update attendance to an event.
        TODO: This is obviously pretty nasty but it'll be changed soon.
        """

        collection_url = build_url(host, [cls.resource_fragment, event_id, 'attendees'])
        item_url = collection_url + '/' + str(profile_id)

        # See if there is an attendance entry for this profile
        try:
            response = requests.get(item_url, params={'access_token': access_token})
        except RequestException:
            raise

        # If it is not found, POST an attendance
        if response.status_code == 404:
            try:
                print 'Not found, posting to ' + collection_url
                post_response = requests.post(collection_url, attendance_data, params={'access_token': access_token})
            except RequestException:
                raise

            try:
                post_response.json()
            except ValueError:
                raise APIException('Invalid JSON returned')

            return

        # Attendance record exists, so update it with PUT
        elif response.status_code >= 200 and response.status_code < 400:

            try:
                print 'Found, putting to ' + item_url
                put_response = requests.post(
                    item_url,
                    data=attendance_data,
                    params={'method': 'PUT', 'access_token': access_token}
                )
            except RequestException:
                raise

            try:
                put_response.json()
            except ValueError:
                raise APIException('Invalid JSON returned')

            return

        else:
            raise APIException(response.content)


class Poll(APIResource):
    resource_fragment = 'polls'

    @classmethod
    def retrieve(cls, host, id=None, offset=None, access_token=None):
        resource = super(Poll, cls).retrieve(host, id, offset, access_token)
        resource = cls.create_linkmap(resource)
        return APIResource.process_timestamp(resource)


class Comment(APIResource):
    resource_fragment = 'comments'

    @classmethod
    def retrieve(cls, host, id=None, offset=None, access_token=None):
        resource = super(Comment, cls).retrieve(host, id, offset, access_token)
        resource = cls.create_linkmap(resource)
        return APIResource.process_timestamp(resource)

    @classmethod
    def create(cls, host, data, access_token):
        resource = super(Comment, cls).create(host, data, access_token)
        resource = cls.create_linkmap(resource)
        return resource

    @classmethod
    def update(cls, host, data, id, access_token):
        resource = super(Comment, cls).update(host, data, id, access_token)
        resource = cls.create_linkmap(resource)
        return resource


class GeoCode():
    """
    This is simply request proxying, so don't attempt formatting
    or error recovery.
    """

    @classmethod
    def retrieve(cls, host, q, access_token):
        """
        Forward a geocode request (q) to the API.
        """
        params = {'q': q}
        headers = {'Authorization': 'Bearer %s' % access_token}
        response = requests.get(build_url(host, ['geocode']), params=params, headers=headers)
        return response.content
