import json

import requests
from requests import RequestException

from dateutil.parser import parse as parse_timestamp

from microcosm.api.exceptions import APIException
from microweb.helpers import DateTimeEncoder
from microweb.helpers import build_url
from microweb.helpers import join_path_fragments


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

    @staticmethod
    def process_response(url, response):
        try:
            resource = response.json()
        except ValueError:
            raise APIException('Response is not valid json:\n %s' % response.content, 500)
        if resource['error']:
            raise APIException(resource['error'], response.status_code)
        if not resource['data']:
            raise APIException('No data returned at: %s' % url)
        return resource['data']

    @staticmethod
    def make_request_headers(access_token=None):
        headers = {'Accept-Encoding': 'application/json'}
        if access_token:
            headers['Authorization'] = 'Bearer %s' % access_token
        return headers

    @staticmethod
    def retrieve(url, params, headers):
        """
        Fetch an API resource and handle any errors.
        """

        response = requests.get(url, params=params, headers=headers)
        return APIResource.process_response(url, response)

    @staticmethod
    def create(url, data, params, headers):
        """
        Create an API resource and handle any errors.
        """

        headers['Content-Type'] = 'application/json'
        response = requests.post(url, data=data, params=params, headers=headers)
        return APIResource.process_response(url, response)

    @staticmethod
    def update(url, data, params, headers):
        """
        Update an API resource with PUT and handle any errors.
        """

        # Override HTTP method on API
        params['method'] = 'PUT'
        headers['Content-Type'] = 'application/json'
        response = requests.post(url, data=data, params=params, headers=headers)
        return APIResource.process_response(url, response)

    @staticmethod
    def delete(url, params, headers):
        """
        Delete an API resource. A 'data' object is never returned by a delete, so only
        raises an exception if 'error' is non-empty or the response cannot be parsed.
        """

        params['method'] = 'DELETE'
        response = requests.post(url, params=params, headers=headers)
        try:
            resource = response.json()
        except ValueError:
            raise APIException('The API has returned invalid json: %s' % response.content, 500)
        if resource['error']:
            raise APIException(resource['error'], response.status_code)


class Site(object):
    """
    Represents the current site (title, logo, etc.).
    """

    api_path_fragment = 'site'

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

    @staticmethod
    def retrieve(host):
        url = build_url(host, [Site.api_path_fragment])
        resource = APIResource.retrieve(url, {}, {})
        return Site(resource)


class User(object):
    """
    User API resource. A user is only defined once across the platform
    (and is thus multi-site). A Profile is site specific, and associates
    a given user and site.
    """

    api_path_fragment = 'users'

    def __init__(self, data):
        self.email = data['email']

    @staticmethod
    def retrieve(host, id, access_token):
        url = build_url(host, [User.api_path_fragment, id])
        resource = APIResource.retrieve(url, {}, APIResource.make_request_headers(access_token))
        return User(resource)


class WhoAmI(object):
    """
    WhoAmI returns the profile of the currently logged-in user.
    """

    api_path_fragment = 'whoami'

    @staticmethod
    def retrieve(host, access_token):
        url = build_url(host, [WhoAmI.api_path_fragment])
        resource = APIResource.retrieve(url, {}, APIResource.make_request_headers(access_token))
        return Profile(resource)


class Profile(object):
    """
    Represents a user profile belonging to a specific site.
    """

    api_path_fragment = 'profiles'

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
        if data.get('avatar'): self.avatar = data['avatar']
        if data.get('meta'): self.meta = Meta(data['meta'])

        if not summary:
            self.style_id = data['styleId']
            self.item_count = data['itemCount']
            self.comment_count = data['commentCount']
            self.created = parse_timestamp(data['created'])
            self.last_active = parse_timestamp(data['lastActive'])
            self.banned = data['banned']
            self.admin = data['admin']

    @staticmethod
    def retrieve(host, id, access_token=None):
        url = build_url(host, [Profile.api_path_fragment, id])
        resource = APIResource.retrieve(url, {}, APIResource.make_request_headers(access_token))
        return Profile(resource, summary=False)

    def update(self, host, access_token):
        url = build_url(host, [Profile.api_path_fragment, self.id])
        payload = json.dumps(self.as_dict, cls=DateTimeEncoder)
        resource = APIResource.update(url, payload, {}, APIResource.make_request_headers(access_token))
        return Profile(resource, summary=False)

    @property
    def as_dict(self):
        repr = {}
        if hasattr(self, 'id'): repr['id'] = self.id
        if hasattr(self, 'site_id'): repr['siteId'] = self.site_id
        if hasattr(self, 'user_id'): repr['userId'] = self.user_id
        if hasattr(self, 'profile_name'): repr['profileName'] = self.profile_name
        if hasattr(self, 'visible'): repr['visible'] =  self.visible
        if hasattr(self, 'avatar'): repr['avatar'] = self.avatar
        if hasattr(self, 'style_id'): repr['styleId'] = self.style_id
        if hasattr(self, 'item_count'): repr['itemCount'] = self.item_count
        if hasattr(self, 'comment_count'): repr['commentCount'] = self.comment_count
        if hasattr(self, 'created'): repr['created'] = self.created
        if hasattr(self, 'last_active'): repr['lastActive'] = self.last_active
        if hasattr(self, 'banned'): repr['banned'] = self.banned
        if hasattr(self, 'admin'): repr['admin'] = self.admin
        return repr


class Microcosm(APIResource):
    """
    Represents a single microcosm, containing items (conversations, events, ...)
    """

    api_path_fragment = 'microcosms'

    @classmethod
    def from_api_response(cls, data):
        microcosm = Microcosm()
        if data.get('id'): microcosm.id = data['id']
        if data.get('siteId'): microcosm.site_id = data['siteId']
        if data.get('visibility'): microcosm.visibility = data['visibility']
        if data.get('title'): microcosm.title = data['title']
        if data.get('description'): microcosm.description = data['description']
        if data.get('moderators'): microcosm.moderators = data['moderators']
        if data.get('editReason'): microcosm.edit_reason = data['editReason']
        if data.get('meta'): microcosm.meta = Meta(data['meta'])
        if data.get('items'): microcosm.items = PaginatedList(data['items'], Item)
        return microcosm

    @classmethod
    def from_create_form(cls, data):
        return Microcosm.from_api_response(data)

    @classmethod
    def from_edit_form(cls, data):
        return Microcosm.from_api_response(data)

    @classmethod
    def from_summary(cls, data):
        microcosm = Microcosm.from_api_response(data)
        if data.get('mostRecentUpdate'):
            microcosm.most_recent_update = Item.from_summary(data['mostRecentUpdate'])
        if data.get('totalItems'): microcosm.total_items = data['totalItems']
        if data.get('totalComments'): microcosm.total_comments = data['totalComments']
        return microcosm

    @staticmethod
    def retrieve(host, id, offset=None, access_token=None):
        url = build_url(host, [Microcosm.api_path_fragment, id])
        params = {'offset': offset} if offset else {}
        resource = APIResource.retrieve(url, params, APIResource.make_request_headers(access_token))
        return Microcosm.from_api_response(resource)

    def create(self, host, access_token):
        url = build_url(host, [Microcosm.api_path_fragment])
        payload = json.dumps(self.as_dict, cls=DateTimeEncoder)
        resource = APIResource.create(url, payload, {}, APIResource.make_request_headers(access_token))
        return Microcosm.from_api_response(resource)

    def update(self, host, access_token):
        url = build_url(host, [Microcosm.api_path_fragment, self.id])
        payload = json.dumps(self.as_dict, cls=DateTimeEncoder)
        resource = APIResource.update(url, payload, {}, APIResource.make_request_headers(access_token))
        return Microcosm.from_api_response(resource)

    def delete(self, host, access_token):
        url = build_url(host, [Microcosm.api_path_fragment, self.id])
        APIResource.delete(url, {}, APIResource.make_request_headers(access_token))

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


class MicrocosmList(object):
    """
    Represents a list of microcosms for a given site.
    """

    api_path_fragment = 'microcosms'

    def __init__(self, data):
        self.microcosms = PaginatedList(data['microcosms'], Microcosm)
        self.meta = Meta(data['meta'])

    @staticmethod
    def retrieve(host, offset=None, access_token=None):
        url = build_url(host, [MicrocosmList.api_path_fragment])
        params = {'offset': offset} if offset else {}
        resource = APIResource.retrieve(url, params, APIResource.make_request_headers(access_token))
        return MicrocosmList(resource)


class Item(object):
    """
    Represents an item contained within a microcosm. Only used when
    fetching a single microcosm to represent the list of items
    contained within.
    """

    @classmethod
    def from_summary(cls, data):
        item = cls()
        item.id = data['id']
        item.item_type = data['itemType']
        item.microcosm_id = data['microcosmId']
        item.title = data['title']
        item.total_comments = data['totalComments']
        item.total_views = data['totalViews']
        if data.get('lastCommentId'): item.last_comment_id = data['lastCommentId']
        if data.get('lastCommentCreatedBy'):
            item.last_comment_created_by = Profile(data['lastCommentCreatedBy'])
        if data.get('lastCommentCreated'):
            item.last_comment_created = parse_timestamp(data['lastCommentCreated'])
        item.meta = Meta(data['meta'])
        return item


class PaginatedList(object):
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
        self.items = [list_item_cls.from_summary(item) for item in item_list['items']]
        self.links = {}
        for item in item_list['links']:
            self.links[item['rel']] = item['href']


class Meta(object):
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

    api_path_fragment = 'conversations'

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

    @staticmethod
    def retrieve(host, id, offset=None, access_token=None):
        url = build_url(host, [Conversation.api_path_fragment, id])
        params = {'offset': offset} if offset else {}
        resource = APIResource.retrieve(url, params, APIResource.make_request_headers(access_token))
        return Conversation.from_api_response(resource)

    def create(self, host, access_token):
        url = build_url(host, [Conversation.api_path_fragment])
        payload = json.dumps(self.as_dict(), cls=DateTimeEncoder)
        resource = APIResource.create(url, payload, {}, APIResource.make_request_headers(access_token))
        return Conversation.from_api_response(resource)

    def update(self, host, access_token):
        url = build_url(host, [Conversation.api_path_fragment, self.id])
        payload = json.dumps(self.as_dict(update=True), cls=DateTimeEncoder)
        resource = APIResource.update(url, payload, {}, APIResource.make_request_headers(access_token))
        return Conversation.from_api_response(resource)

    def delete(self, host, access_token):
        url = build_url(host, [Conversation.api_path_fragment, self.id])
        APIResource.delete(url, {}, APIResource.make_request_headers(access_token))

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

    api_path_fragment = 'events'

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
        event.rsvp_limit = data['rsvpLimit']

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
        if hasattr(self, 'rsvp_limit'): repr['rsvpLimit'] = self.rsvp_limit
        if hasattr(self, 'rsvp_spaces'): repr['rsvpSpaces'] = self.rsvp_spaces

        return repr

    @staticmethod
    def retrieve(host, id, offset=None, access_token=None):
        url = build_url(host, [Event.api_path_fragment, id])
        params = {'offset': offset} if offset else {}
        resource = APIResource.retrieve(url, params, APIResource.make_request_headers(access_token))
        return Event.from_api_response(resource)

    def create(self, host, access_token):
        url = build_url(host, [Event.api_path_fragment])
        payload = json.dumps(self.as_dict(), cls=DateTimeEncoder)
        resource = APIResource.create(url, payload, {}, APIResource.make_request_headers(access_token))
        return Event.from_api_response(resource)

    def update(self, host, access_token):
        url = build_url(host, [Event.api_path_fragment, self.id])
        payload = json.dumps(self.as_dict(update=True), cls=DateTimeEncoder)
        resource = APIResource.update(url, payload, {}, APIResource.make_request_headers(access_token))
        return Event.from_api_response(resource)

    def delete(self, host, access_token):
        url = build_url(host, [Event.api_path_fragment, self.id])
        APIResource.delete(url, {}, APIResource.make_request_headers(access_token))


    def get_attendees(self, host, access_token=None):
        """
        Retrieve a list of attendees for an event.
        TODO: pagination support
        """

        url = build_url(host, [Event.api_path_fragment, self.id, 'attendees'])
        resource = APIResource.retrieve(url, {}, APIResource.make_request_headers())
        return AttendeeList(resource)

    @classmethod
    def rsvp(cls, host, event_id, profile_id, attendance_data, access_token):
        """
        Create or update attendance to an event.
        TODO: This is obviously pretty nasty but it'll be changed when PATCH support is added.
        """

        collection_url = build_url(host, [cls.api_path_fragment, event_id, 'attendees'])
        item_url = '%s/%d' % (collection_url, profile_id)

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


class AttendeeList(object):
    """
    Represents a paginated list of event attendees.
    """

    def __init__(self, data):
        self.items = PaginatedList(data['attendees'], Attendee)
        self.meta = Meta(data['meta'])


class Attendee(object):

    @classmethod
    def from_summary(cls, data):
        attendee = cls()
        attendee.attendee_id = data['attendeeId']
        attendee.attendee = Attendee.AttendeeRecord(data['attendee'])
        attendee.rsvp = data['rsvp']
        attendee.rsvpd_on = data['rsvpdOn']
        attendee.meta = Meta(data['meta'])
        return attendee

    class AttendeeRecord(object):
        def __init__(self, data):
            self.site_id = data['siteId']
            self.user_id = data['userId']
            self.profile_name = data['profileName']
            self.visible = data['visible']
            if data.get('avatar'):
                self.avatar = data['avatar']
            self.meta = Meta(data['meta'])


class Comment(APIResource):
    """
    Represents a single comment.
    """

    api_path_fragment = 'comments'

    @classmethod
    def from_api_response(cls, data):
        comment = cls()
        comment.id = data['id']
        comment.item_type = data['itemType']
        comment.item_id = data['itemId']
        comment.revisions = data['revisions']
        comment.in_reply_to = data['inReplyTo']
        comment.attachments = data['attachments']
        comment.first_line = data['firstLine']
        comment.markdown = data['markdown']
        comment.html = data['html']
        comment.meta = Meta(data['meta'])
        return comment

    @classmethod
    def from_summary(cls, data):
        return Comment.from_api_response(data)

    @classmethod
    def from_create_form(cls, data):
        comment = cls()
        comment.item_type = data['itemType']
        comment.item_id = data['itemId']
        comment.in_reply_to = data['inReplyTo']
        comment.markdown = data['markdown']
        return comment

    @classmethod
    def from_edit_form(cls, data):
        comment = Comment.from_create_form(data)
        comment.id = data['id']
        return comment

    @staticmethod
    def retrieve(host, id, offset=None, access_token=None):
        url = build_url(host, [Comment.api_path_fragment, id])
        params = {'offset': offset} if offset else {}
        resource = APIResource.retrieve(url, params, APIResource.make_request_headers(access_token))
        return Comment.from_api_response(resource)

    def create(self, host, access_token):
        url = build_url(host, [Comment.api_path_fragment])
        payload = json.dumps(self.as_dict, cls=DateTimeEncoder)
        resource = APIResource.create(url, payload, {}, APIResource.make_request_headers(access_token))
        return Comment.from_api_response(resource)

    def update(self, host, access_token):
        url = build_url(host, [Comment.api_path_fragment, self.id])
        payload = json.dumps(self.as_dict, cls=DateTimeEncoder)
        resource = APIResource.update(url, payload, {}, APIResource.make_request_headers(access_token))
        return Comment.from_api_response(resource)

    def delete(self, host, access_token):
        url = build_url(host, [Comment.api_path_fragment, self.id])
        APIResource.delete(url, {}, APIResource.make_request_headers(access_token))

    @property
    def as_dict(self):
        repr = {}
        if hasattr(self, 'id'): repr['id'] = self.id
        if hasattr(self, 'item_type'): repr['itemType'] = self.item_type
        if hasattr(self, 'item_id'): repr['itemId'] = self.item_id
        if hasattr(self, 'revisions'): repr['revisions'] = self.revisions
        if hasattr(self, 'in_reply_to'): repr['inReplyTo'] = self.in_reply_to
        if hasattr(self, 'attachments'): repr['attachments'] = self.attachments
        if hasattr(self, 'first_line'): repr['firstLine'] = self.first_line
        if hasattr(self, 'markdown'): repr['markdown'] = self.markdown
        if hasattr(self, 'html'): repr['html'] = self.html
        if hasattr(self, 'meta'): repr['meta'] = self.meta
        return repr


class GeoCode(object):
    """
    Used for proxying geocode requests to the backend.
    """

    @classmethod
    def retrieve(cls, host, q, access_token):
        """
        Forward a geocode request (q) to the API.
        """
        params = {'q': q}
        headers = APIResource.make_request_headers(access_token)
        response = requests.get(build_url(host, ['geocode']), params=params, headers=headers)
        return response.content


class FileMetadata(object):
    """
    For managing user-uploaded files.
    TODO: manage multiple uploads
    """

    api_path_fragment = 'files'

    @classmethod
    def from_create_form(cls, file_upload):
        file_metadata = cls()
        file_metadata.file = {'files': file_upload.read()}
        return file_metadata

    @classmethod
    def from_api_response(cls, data):
        file_metadata = cls()
        file_metadata.created = parse_timestamp(data[0]['created'])
        file_metadata.file_size = data[0]['fileSize']
        file_metadata.file_hash = data[0]['fileHash']
        file_metadata.mime_type = data[0]['mimeType']
        return file_metadata

    def create(self, host, access_token):
        url = build_url(host, [FileMetadata.api_path_fragment])
        headers = APIResource.make_request_headers(access_token)
        response = APIResource.process_response(url, requests.post(url, files=self.file, headers=headers))
        return FileMetadata.from_api_response(response)


class Attachment(object):
    """
    Represents the relation between a file and a profile or comment.
    TODO: parse attachment list in response (currently create only signals
    errors).
    """

    @staticmethod
    def create(host, file_hash, profile_id=None, comment_id=None, access_token=None):
        if profile_id:
            url = build_url(host, ['profiles', profile_id, 'attachments'])
        elif comment_id:
            url = build_url(host, ['comments', comment_id, 'attachments'])
        else:
            raise AssertionError, 'You must supply a profile_id or comment_id to attach to'

        attachment = {'FileHash': file_hash}
        headers = APIResource.make_request_headers(access_token)
        return APIResource.process_response(url, requests.post(url, data=attachment, headers=headers))