import json

import requests
from requests import RequestException

from dateutil.parser import parse as parse_timestamp

from microcosm.api.exceptions import APIException
from microweb.helpers import DateTimeEncoder
from microweb.helpers import build_url

RESOURCE_PLURAL = {
    'event': 'events',
    'conversation': 'conversations',
    'poll': 'polls',
    'comment': 'comments',
    'profile': 'profiles',
    'user': 'users',
    'site': 'sites',
}

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

    def __init__(self, data):
        self.site_id = data['siteId']
        self.title = data['title']
        self.description = data['description']
        self.subdomain_key = data['subdomainKey']
        self.domain = data['domain']
        self.owned_by = Profile(data['ownedBy'])

        # Site themes are optional
        if data.get('logoUrl'): self.logo_url = data['logoUrl']
        if data.get('themeId'): self.theme_id = data['themeId']
        if data.get('headerBackgroundUrl'):
            self.header_background_url = data['headerBackgroundUrl']

    @classmethod
    def retrieve(cls, host):
        resource = super(Site, cls).retrieve(host)
        return Site(resource)


class User(APIResource):
    """
    User API resource. A user is only defined once across the platform
    (and is thus multi-site). A Profile is site specific, and associates
    a given user and site.
    """

    resource_fragment = 'users'

    def __init__(self, data):
        self.email = data['email']

    @classmethod
    def retrieve(cls, host, id, access_token):
        resource = super(User, cls).retrieve(host, id=id, access_token=access_token)
        return User(resource)


class WhoAmI(APIResource):
    """
    WhoAmI returns the profile of the currently logged-in user.
    """

    resource_fragment = 'whoami'

    @classmethod
    def retrieve(cls, host, access_token):
        resource = super(WhoAmI, cls).retrieve(host, access_token=access_token)
        return Profile(resource)


class Profile(APIResource):
    """
    Represents a user profile belonging to a specific site.
    """

    resource_fragment = 'profiles'

    def __init__(self, data, summary=True):
        """
        We're permissive about the data passed in, since it may
        be a PUT or PATCH operation and not have all the expected keys.
        """

        if data.get('id'): self.id = data['id']
        if data.get('siteId'): self.site_id = data['siteId']
        if data.get('userId'): self.user_id = data['userId']
        if data.get('profileName'): self.profile_name = data['profileName']
        if data.get('visible'): self.visible = data['visible']
        if data.get('gravatar'): self.gravatar = data['gravatar']
        if data.get('meta'): self.meta = Meta(data['meta'])

        if not summary:
            self.style_id = data['styleId']
            self.item_count = data['itemCount']
            self.comment_count = data['commentCount']
            self.created = parse_timestamp(data['created'])
            self.last_active = parse_timestamp(data['lastActive'])
            self.banned = data['banned']
            self.admin = data['admin']

    @classmethod
    def retrieve(cls, host, id, access_token=None):
        resource = super(Profile, cls).retrieve(host, id, access_token=access_token)
        return Profile(resource)

    @property
    def as_dict(self):
        repr = {}
        if hasattr(self, 'id'): repr['id'] = self.id
        if hasattr(self, 'site_id'): repr['siteId'] = self.site_id
        if hasattr(self, 'user_id'): repr['userId'] = self.user_id
        if hasattr(self, 'profile_name'): repr['profileName'] = self.profile_name
        if hasattr(self, 'visible'): repr['visible'] =  self.visible
        if hasattr(self, 'gravatar'): repr['gravatar'] = self.gravatar
        if hasattr(self, 'style_id'): repr['styleId'] = self.style_id
        if hasattr(self, 'item_count'): repr['itemCount'] = self.item_count
        if hasattr(self, 'comment_count'): repr['commentCount'] = self.comment_count
        if hasattr(self, 'created'): repr['created'] = self.created
        if hasattr(self, 'last_active'): repr['lastActive'] = self.last_active
        if hasattr(self, 'banned'): repr['banned']
        if hasattr(self, 'admin'): repr['admin']
        return repr


class Microcosm(APIResource):
    """
    Represents a single microcosm, containing items (conversations, events, ...)
    """

    resource_fragment = 'microcosms'

    def __init__(self, data, summary=False):
        if data.get('id'): self.id = data['id']
        if data.get('siteId'): self.site_id = data['siteId']
        if data.get('visibility'): self.visibility = data['visibility']
        if data.get('title'): self.title = data['title']
        if data.get('description'): self.description = data['description']
        if data.get('moderators'): self.moderators = data['moderators']
        if data.get('editReason'): self.edit_reason = data['editReason']
        if data.get('meta'): self.meta = Meta(data['meta'])

        if summary:
            if data.get('mostRecentUpdate'):
                self.most_recent_update = Item(data['mostRecentUpdate'])
            if data.get('totalItems'): self.total_items = data['totalItems']
            if data.get('totalComments'): self.total_comments = data['totalComments']
        else:
            if data.get('items'): self.items = PaginatedList(data['items'], Item)

    @classmethod
    def retrieve(cls, host, id, offset=None, access_token=None):
        resource = super(Microcosm, cls).retrieve(host, id, offset, access_token)
        return Microcosm(resource, summary=False)

    @property
    def as_dict(self):
        repr = {}
        if hasattr(self, 'id'): repr['id'] = self.id
        if hasattr(self, 'site_id'): repr['siteId'] = self.site_id
        if hasattr(self, 'visibility'): repr['visibility'] = self.visibility
        if hasattr(self, 'title'): repr['title'] = self.title
        if hasattr(self, 'description'): repr['description'] = self.description
        if hasattr(self, 'moderators'): repr['moderators'] = self.moderators
        if hasattr(self, 'meta'): repr['meta'] = self.meta
        if hasattr(self, 'most_recent_update'): repr['mostRecentUpdate'] = self.most_recent_update
        if hasattr(self, 'total_items'): repr['totalItems'] = self.total_items
        if hasattr(self, 'total_comments'): repr['totalComments'] = self.total_comments
        if hasattr(self, 'items'): repr['items'] = self.items
        if hasattr(self, 'edit_reason'): repr['meta'] = dict(editReason=self.edit_reason)
        return repr


class MicrocosmList(APIResource):
    """
    Represents a list of microcosms for a given site.
    """

    resource_fragment = 'microcosms'

    def __init__(self, data):
        self.microcosms = PaginatedList(data['microcosms'], Microcosm)
        self.meta = Meta(data['meta'])

    @classmethod
    def retrieve(cls, host, offset=None, access_token=None):
        resource = super(MicrocosmList, cls).retrieve(host, offset=offset, access_token=access_token)
        return MicrocosmList(resource)


class Item():
    """
    Represents an item contained within a microcosm. Only used when
    fetching a single microcosm to represent the list of items
    contained within.
    """

    def __init__(self, data, summary=None):
        self.id = data['id']
        self.item_type = data['itemType']
        self.microcosm_id = data['microcosmId']
        self.title = data['title']
        self.total_comments = data['totalComments']
        self.total_views = data['totalViews']
        if data.get('lastCommentId'): self.last_comment_id = data['lastCommentId']
        if data.get('lastCommentCreatedBy'):
            self.last_comment_created_by = Profile(data['lastCommentCreatedBy'])
        if data.get('lastCommentCreated'):
            self.last_comment_created = parse_timestamp(data['lastCommentCreated'])
        self.meta = Meta(data['meta'])


class PaginatedList():
    """
    Generic list of items and pagination metadata (total, number of pages, etc.).
    """

    def __init__(self, item_list, list_item_cls):
        self.total = item_list['total']
        self.limit = item_list['limit']
        self.offset = item_list['offset']
        self.max_offset = item_list['maxOffset']
        self.total_pages = item_list['totalPages']
        self.page = item_list['page']
        self.type = item_list['type']
        self.items = [list_item_cls(item, summary=True) for item in item_list['items']]
        self.links = {}
        for item in item_list['links']:
            self.links[item['rel']] = item['href']


class Meta():
    """
    Represents a resource 'meta' type, including creation time/user,
    flags, links, and permissions.
    """

    def __init__(self, data):
        if data.get('created'): self.created = (data['created'])
        if data.get('createdBy'): self.created_by = Profile(data['createdBy'])
        if data.get('edited'): self.created = (data['edited'])
        if data.get('editedBy'): self.created_by = Profile(data['editedBy'])
        if data.get('flags'): self.flags = data['flags']
        if data.get('permissions'): self.permissions = PermissionSet(data['permissions'])
        if data.get('links'):
            self.links = {}
            for item in data['links']:
                self.links[item['rel']] = item['href']


class PermissionSet(object):
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
    def from_api_response(cls, data):
        conversation = cls()
        conversation.id = data['id']
        conversation.microcosm_id = data['microcosmId']
        conversation.title = data['title']
        conversation.comments = PaginatedList(data['comments'], Comment)
        conversation.meta = Meta(data['meta'])
        return conversation

    @classmethod
    def from_create_form(cls, data):
        conversation = cls()
        conversation.microcosm_id = data['microcosmId']
        conversation.title = data['title']
        return conversation

    @classmethod
    def from_edit_form(cls, data):
        conversation = Conversation.from_create_form(data)
        conversation.id = data['id']
        conversation.meta = {'editReason': data['editReason']}
        return conversation

    @classmethod
    def retrieve(cls, host, id=None, offset=None, access_token=None):
        resource = super(Conversation, cls).retrieve(host, id, offset, access_token)
        return Conversation.from_api_response(resource)

    def create(self, host, access_token):
        resource = super(Conversation, self.__class__).create(host, self.as_dict(), access_token)
        return Conversation.from_api_response(resource)

    def update(self, host, id, access_token):
        resource = super(Conversation, self.__class__).update(host, self.as_dict(update=True), id, access_token)
        return Conversation.from_api_response(resource)

    def as_dict(self, update=False):
        repr = {}

        if update:
            repr['id'] = self.id
            repr['meta'] = self.meta

        repr['microcosmId'] = self.microcosm_id
        repr['title'] = self.title
        return repr


class Event(APIResource):
    """
    Represents an event (event details and list of comments).
    """

    resource_fragment = 'events'

    @classmethod
    def from_api_response(cls, data):
        event = cls()

        event.id = data['id']
        event.microcosm_id = data['microcosmId']
        event.title = data['title']
        event.when = parse_timestamp(data['when'])
        event.duration = data['duration']
        event.status = data['status']

        # Event location
        event.where = data['where']
        event.lat = data['lat']
        event.lon = data['lon']
        event.north = data['north']
        event.east = data['east']
        event.south = data['south']
        event.west = data['west']

        event.comments = PaginatedList(data['comments'], Comment)
        event.meta = Meta(data['meta'])

        # RSVP numbers are optional
        if data.get('rsvpAttend'): event.rsvp_attend = data['rsvpAttend']
        if data.get('rsvpLimit'): event.rsvp_limit = data['rsvpLimit']
        if data.get('rsvpSpaces'): event.rsvp_spaces = data['rsvpSpaces']

        return event

    @classmethod
    def from_create_form(cls, data):
        event = cls()

        event.microcosm_id = data['microcosmId']
        event.title = data['title']
        # This is already type(datetime.datetime) so need not be parsed
        event.when = data['when']
        event.duration = data['duration']

        # Event location
        event.where = data['where']
        event.lat = data['lat']
        event.lon = data['lon']
        event.north = data['north']
        event.east = data['east']
        event.south = data['south']
        event.west = data['west']

        return event

    @classmethod
    def from_edit_form(cls, data):
        """
        Similar to from_create_form, but 'editReason' is expected in
        the meta object for Event updates, and the ID is known.
        """

        event = Event.from_create_form(data)
        event.id = data['id']
        event.meta = {'editReason': data['editReason']}
        return event

    def as_dict(self, update=False):
        """
        Renders Event as a dictionary for POST/PUT to API. 'update' indicates
        whether this is an update action instead of a create action.
        """

        repr = {}

        if update:
            repr['id'] = self.id
            repr['meta'] = self.meta

        repr['microcosmId'] = self.microcosm_id
        repr['title'] = self.title
        repr['when'] = self.when
        repr['duration'] = self.duration

        # Event location
        repr['where'] = self.where
        repr['lat'] = self.lat
        repr['lon'] = self.lon
        repr['north'] = self.north
        repr['east'] = self.east
        repr['south'] = self.south
        repr['west'] = self.west

        # RSVP limit is optional
        if hasattr(self, 'rsvp_attend'): repr['rsvpAttend'] = self.rsvp_attend
        if hasattr(self, 'rsvp_limit'): repr['rsvpLimit'] = self.rsvp_attend
        if hasattr(self, 'rsvp_spaces'): repr['rsvpSpaces'] = self.rsvp_attend

        return repr

    @classmethod
    def retrieve(cls, host, id, offset=None, access_token=None):
        resource = super(Event, cls).retrieve(host, id, offset, access_token)
        return Event.from_api_response(resource)

    def create(self, host, access_token):
        resource = super(Event, self.__class__).create(host, self.as_dict(), access_token)
        return Event.from_api_response(resource)

    def update(self, host, id, access_token):
        resource = super(Event, self.__class__).update(host, self.as_dict(update=True), id, access_token)
        return Event.from_api_response(resource)

    def get_attendees(self, host, access_token=None):
        """
        Retrieve a list of attendees for an event.
        TODO: pagination support
        """

        resource_url = build_url(host, [Event.resource_fragment, self.id, 'attendees'])
        resource = APIResource.retrieve(host, id=id, access_token=access_token, url_override=resource_url)
        return AttendeeList(resource)

    @classmethod
    def rsvp(cls, host, event_id, profile_id, attendance_data, access_token):
        """
        Create or update attendance to an event.
        TODO: This is obviously pretty nasty but it'll be changed when PATCH support is added.
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


class AttendeeList(APIResource):
    """
    Represents a paginated list of event attendees.
    """

    def __init__(self, data):
        self.items = PaginatedList(data['attendees'], Attendee)
        self.meta = Meta(data['meta'])


class Attendee(object):

    def __init__(self, data, summary=None):
        self.attendee_id = data['attendeeId']
        self.attendee = Attendee.AttendeeRecord(data['attendee'])
        self.rsvp = data['rsvp']
        self.rsvpd_on = data['rsvpdOn']
        self.meta = Meta(data['meta'])

    class AttendeeRecord(object):
        def __init__(self, data):
            self.site_id = data['siteId']
            self.user_id = data['userId']
            self.profile_name = data['profileName']
            self.visible = data['visible']
            self.gravatar = data['gravatar']
            self.meta = Meta(data['meta'])


class Comment(APIResource):
    """
    Represents a single comment.
    """

    resource_fragment = 'comments'

    def __init__(self, data, summary=None):
        self.id = data['id']
        self.item_type = data['itemType']
        self.item_id = data['itemId']
        self.revisions = data['revisions']
        self.in_reply_to = data['inReplyTo']
        self.attachments = data['attachments']
        self.first_line = data['firstLine']
        self.markdown = data['markdown']
        self.html = data['html']
        self.meta = Meta(data['meta'])

    @classmethod
    def retrieve(cls, host, id, offset=None, access_token=None):
        resource = super(Comment, cls).retrieve(host, id, offset, access_token)
        return Comment(resource)

    @classmethod
    def create(cls, host, data, access_token):
        resource = super(Comment, cls).create(host, data, access_token)
        return Comment(resource)

    @classmethod
    def update(cls, host, data, id, access_token):
        resource = super(Comment, cls).update(host, data, id, access_token)
        return Comment(resource)

    @property
    def as_dict(self):
        repr = {}
        repr['id'] = self.id
        repr['itemType'] = self.item_type
        repr['itemId'] = self.item_id
        repr['revisions'] = self.revisions
        repr['inReplyTo'] = self.in_reply_to
        repr['attachments'] = self.attachments
        repr['firstLine'] = self.first_line
        repr['markdown'] = self.markdown
        repr['html'] = self.html
        repr['meta'] = self.meta
        return repr


class GeoCode():
    """
    Used for proxying geocode requests to the backend.
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


class Authentication(APIResource):
    """
    Stub for making calls to /auth for creating and destroying access tokens.
    TODO: shift the access_token/id logic in APIResource.delete to here.
    """

    resource_fragment = 'auth'
