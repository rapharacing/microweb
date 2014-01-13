import json
import datetime

import requests
from requests import RequestException

from dateutil.parser import parse as parse_timestamp

from microcosm.api.exceptions import APIException
from microweb.helpers import DateTimeEncoder

from settings import API_VERSION
from settings import API_PATH
from settings import API_SCHEME
from settings import API_DOMAIN_NAME
from settings import DEBUG
from settings import MEMCACHE_HOST
from settings import MEMCACHE_PORT

import logging

import pylibmc as memcache

logger = logging.getLogger('microcosm.middleware')
mc = memcache.Client(['%s:%d' % (MEMCACHE_HOST, MEMCACHE_PORT)])

RESOURCE_PLURAL = {
    'event': 'events',
    'conversation': 'conversations',
    'poll': 'polls',
    'comment': 'comments',
    'profile': 'profiles',
    'user': 'users',
    'site': 'sites',
    'microcosm': 'microcosms',
    'huddle': 'huddles',
}

# Item types that can have comments
COMMENTABLE_ITEM_TYPES = [
    'event',
    'conversation',
    'poll',
    'huddle'
]


def build_url(host, path_fragments):
    """
    urljoin and os.path.join don't behave exactly as we want, so
    here's a different wheel.

    As per RFC 3986, authority is composed of hostname[:port] (and optionally
    userinfo, but the microcosm API will never accept these in the URL, so
    we ignore their presence).

    path should be a list of URL fragments. This function will strip separators and
    insert them where needed to form a valid URL.

    The use of + for string concat is deemed acceptable because it is 'fast enough'
    on CPython and we are not going to change interpreter.
    """

    host = host.split(':')[0]
    if host.endswith(API_DOMAIN_NAME):
        url = API_SCHEME + host
    else:
        mc_key = host + '_cname'
        resolved_name = None
        try:
            resolved_name = mc.get(mc_key)
        except memcache.Error as e:
            logger.error('Memcached error: %s' % str(e))

        if resolved_name is None:
            resolved_name = Site.resolve_cname(host)
            mc.set(mc_key, resolved_name)
        url = API_SCHEME + resolved_name
    path_fragments = [API_PATH, API_VERSION] + path_fragments
    url += join_path_fragments(path_fragments)
    return url


def join_path_fragments(path_fragments):
    path = ''

    for fragment in path_fragments:
        if not isinstance(fragment, str):
            fragment = str(fragment)
        if '/' in fragment:
            fragment = fragment.strip('/')
            if '/' in fragment:
                raise AssertionError('Do not use path fragments containing slashes')
        path += ('/' + fragment)
    return path


def discard_querystring(url):
    return url.split('?')[0]


def response_list_to_dict(responses):
    """
    Takes a list of HTTP responses as returned by grequests.map and creates a dict
    with the request url as the key and the response as the value. If the request
    was redirected (as shown by a history tuple on the response), the
    prior request url will be used as the key.
    """

    response_dict = {}
    for response in responses:
        # Only follow one redirect. This is specifically to handle the /whoami
        # case where the client is redirected to /profiles/{id}
        if response.history:
            response_dict[discard_querystring(response.history[0].url)] = \
                APIResource.process_response(response.history[0].url, response)
        else:
            response_dict[discard_querystring(response.url)] = APIResource.process_response(response.url, response)
    return response_dict


def populate_item(itemtype, itemdata):
    if itemtype == 'conversation':
        item = Conversation.from_summary(itemdata)
    elif itemtype == 'comment':
        item = Comment.from_summary(itemdata)
    elif itemtype == 'event':
        item = Event.from_summary(itemdata)
    elif itemtype == 'profile':
        item = Profile.from_summary(itemdata)
    elif itemtype == 'microcosm':
        item = Microcosm.from_summary(itemdata)
    else:
        item = None
    return item


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
        if resource['data'] is None:
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
        response = requests.delete(url, params=params, headers=headers)
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
        self.meta = Meta(data['meta'])

        # Custom tracking is optional
        if data.get('gaWebPropertyId'): self.ga_web_property_id = data['gaWebPropertyId']

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

    @staticmethod
    def resolve_cname(host):
        # TODO: separation of root site API and others
        # TODO: get rid of this string
        url = 'https://microco.sm/api/v1/hosts/' + host
        response = requests.get(url)
        if response.status_code != 200:
            raise APIException('Error resolving CNAME %s' % host, response.status_code)
        print(response.content)
        return response.content


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
    def build_request(host, access_token):
        url = build_url(host, [WhoAmI.api_path_fragment])
        params = {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, access_token):
        url, params, headers = WhoAmI.build_request(host, access_token)
        resource = APIResource.retrieve(url, params=params, headers=headers)
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

    @classmethod
    def from_summary(cls, data):
        profile = Profile(data, summary=True)
        return profile

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

    @staticmethod
    def get_unread_count(host, access_token):
        url = build_url(host, ['updates', 'unread'])
        return APIResource.retrieve(url, {}, headers=APIResource.make_request_headers(access_token))


class ProfileList(object):
    """
    Represents a list of profiles for a given site.
    """

    api_path_fragment = 'profiles'

    def __init__(self, data):
        self.profiles = PaginatedList(data['profiles'], Profile)
        self.meta = Meta(data['meta'])

    @staticmethod
    def build_request(host, offset=None, top=False, q="", following=False, access_token=None):
        url = build_url(host, [ProfileList.api_path_fragment])
        params = {}
        if offset: params['offset'] = offset
        if top: params['top'] = top
        if q: params['q'] = q
        if following: params['following'] = following
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, offset=None, access_token=None):
        url, params, headers = ProfileList.build_request(host, offset, access_token)
        resource = APIResource.retrieve(url, params, headers)
        return ProfileList(resource)

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
    def build_request(host, id, offset=None, access_token=None):
        url = build_url(host, [MicrocosmList.api_path_fragment, id])
        params = {'offset': offset} if offset else {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, id, offset=None, access_token=None):
        url, params, headers = Microcosm.build_request(host, id, offset, access_token)
        resource = APIResource.retrieve(url, params, headers)
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
    def build_request(host, offset=None, access_token=None):
        url = build_url(host, [MicrocosmList.api_path_fragment])
        params = {'offset': offset} if offset else {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, offset=None, access_token=None):
        url, params, headers = MicrocosmList.build_request(host, offset, access_token)
        resource = APIResource.retrieve(url, params, headers)
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
        item.id = data['item']['id']
        item.item_type = data['itemType']
        item.microcosm_id = data['item']['microcosmId']
        item.title = data['item']['title']
        item.total_comments = data['item']['totalComments']
        item.total_views = data['item']['totalViews']
 
        if data['item'].get('lastComment'):
            if data['item']['lastComment'].get('id'):
                item.last_comment_id = data['item']['lastComment']['id']
            if data['item']['lastComment'].get('createdBy'):
                item.last_comment_created_by = Profile(data['item']['lastComment']['createdBy'])
            if data['item']['lastComment'].get('created'):
                item.last_comment_created = parse_timestamp(data['item']['lastComment']['created'])

        item.meta = Meta(data['item']['meta'])

        item.item = populate_item(item.item_type, data['item'])

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
        if item_list.get('items'):
            self.items = [list_item_cls.from_summary(item) for item in item_list['items']]
        else:
            self.items = []
        self.links = {}
        for item in item_list['links']:
            if 'title' in item:
                self.links[item['rel']] = {'href': item['href'], 'title': item['title']}
            else:
                self.links[item['rel']] = {'href': item['href']}


class Meta(object):
    """
    Represents a resource 'meta' type, including creation time/user,
    flags, links, and permissions.
    """

    def __init__(self, data):
        if data.get('created'): self.created = (parse_timestamp(data['created']))
        if data.get('createdBy'): self.created_by = Profile(data['createdBy'])
        if data.get('edited'): self.edited = (parse_timestamp(data['edited']))
        if data.get('editedBy'): self.edited_by = Profile(data['editedBy'])
        if data.get('flags'): self.flags = data['flags']
        if data.get('permissions'): self.permissions = PermissionSet(data['permissions'])
        if data.get('inReplyTo'):
            self.parents = []
            self.parents.append(Comment.from_summary(data['inReplyTo']))
        if data.get('replies'):
            self.children = []
            for item in data['replies']:
                self.children.append(Comment.from_summary(item))
        if data.get('links'):
            self.links = {}
            for item in data['links']:
                if 'title' in item:
                    self.links[item['rel']] = {'href': str.replace(str(item['href']),'/api/v1',''), 'title': item['title']}
                else:
                    self.links[item['rel']] = {'href': str.replace(str(item['href']),'/api/v1','')}
        if data.get('stats'):
            self.stats = {}
            for stat in data['stats']:
                if stat.get('metric'):
                    self.stats[stat['metric']] = stat['value']


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
        self.super_user = data['moderator']
        self.owner = data['owner']


class Watcher(APIResource):

    api_path_fragment = 'watchers'

    def __init__(self, data):
        self.id = data['id']
        self.item_type_id = data['itemTypeId']
        self.item_id = data['itemId']
        self.send_email = data['sendEmail']
        self.send_sms = data['sendSMS']

        if data.get('item'):
            if data.get('itemType') == "conversation":
                self.item = Conversation.from_summary(data['item'])
                self.item_link = '/%s/%s/newest/' % (RESOURCE_PLURAL[data.get('itemType')], self.item_id)

                if data['item'].get('lastCommentCreated'):
                    self.item.last_comment_created = parse_timestamp(data['item']['lastCommentCreated'])
                else:
                    self.item.last_comment_created = parse_timestamp(data['item']['meta']['created'])

            elif data.get('itemType') == "event":
                self.item = Event.from_summary(data['item'])
                self.item_link = '/%s/%s/newest' % (RESOURCE_PLURAL[data.get('itemType')], self.item_id)

                if data['item'].get('lastCommentCreated'):
                    self.item.last_comment_created = parse_timestamp(data['item']['lastCommentCreated'])
                else:
                    self.item.last_comment_created = parse_timestamp(data['item']['meta']['created'])

            elif data.get('itemType') == "microcosm":
                self.item = Microcosm.from_summary(data['item'])
                self.item_link = '/%s/%s' % (RESOURCE_PLURAL[data.get('itemType')], self.item_id)

                if data['item'].get('mostRecentUpdate'):
                    self.item.last_comment_created = parse_timestamp(data['item']['mostRecentUpdate']['meta']['created'])
                else:
                    self.item.last_comment_created = parse_timestamp(data['item']['meta']['created'])

            else:
                self.item_link = '/%s/%s' % (RESOURCE_PLURAL[data.get('itemType')], self.item_id)

    @classmethod
    def from_summary(cls, data):
        return cls(data)

    @staticmethod
    def delete(host, data, access_token):
        url = build_url(host, [Watcher.api_path_fragment, "delete"])
        APIResource.delete(url, data, APIResource.make_request_headers(access_token))

    @staticmethod
    def update(host, data, access_token):
        url = build_url(host, [Watcher.api_path_fragment, "patch"])
        params = {}
        params['method'] = 'PATCH'
        headers = APIResource.make_request_headers(access_token)
        headers['Content-Type'] = 'application/json'
        response = requests.patch(url, data=json.dumps(data), params=params, headers=headers)
        return response

    @staticmethod
    def create(host, data, access_token):
        url = build_url(host, [Watcher.api_path_fragment])
        headers = APIResource.make_request_headers(access_token)
        headers['Content-Type'] = 'application/json'
        response = requests.post(url, json.dumps(data), params={}, headers=headers)
        return response.content


class WatcherList(object):
    """
    List of a user's watchers.
    """

    api_path_fragment = 'watchers'

    def __init__(self, data):
        self.watchers = PaginatedList(data['watchers'], Watcher)

    @staticmethod
    def build_request(host, offset=None, access_token=None):
        url = build_url(host, [WatcherList.api_path_fragment])
        params = {'offset': offset} if offset else {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, offset=None, access_token=None):
        url, params, headers = WatcherList.build_request(host, offset, access_token)
        resource = APIResource.retrieve(url, params, headers)
        return WatcherList(resource)


class UpdateList(object):
    """
    A list of user updates.
    """

    api_path_fragment = 'updates'

    def __init__(self, data):
        self.updates = PaginatedList(data['updates'], Update)
        self.meta = Meta(data['meta'])

    @staticmethod
    def build_request(host, offset=None, access_token=None):
        url = build_url(host, [UpdateList.api_path_fragment])
        params = {'offset': offset} if offset else {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, offset=None, access_token=None):
        url, params, headers = UpdateList.build_request(host, offset, access_token)
        resource = APIResource.retrieve(url, params, headers)
        return UpdateList(resource)


class Update(APIResource):
    """
    Represents a user Update, e.g. a mention by another user.
    """

    api_path_fragment = 'updates'

    @classmethod
    def from_api_response(cls, data):
        update = cls()
        update.id = data['id']
        update.update_type = data['updateType']
        update.item_type = data['itemType']
        update.meta = Meta(data['meta'])

        update.item = populate_item(update.item_type, data['item'])

        if data.get('parentItem'):
            update.parent_item_type = data['parentItemType']
            update.parent_item = populate_item(update.parent_item_type, data['parentItem'])
        else:
            update.parent_item = update.item

        update.item_link = '/%s/%s' % (RESOURCE_PLURAL[update.item_type], update.item.id)

        if update.update_type == 'new_comment':
            update.parent_link = update.parent_item.meta.links['self']['href']
        elif update.update_type == 'reply_to_comment':
            update.profile_link = update.item.meta.created_by.meta.links['self']['href']
            update.parent_link = update.parent_item.meta.links['self']['href']
        elif update.update_type == 'mentioned':
            update.profile_link = update.item.meta.created_by.meta.links['self']['href']
            update.parent_link = update.parent_item.meta.links['self']['href']
        elif update.update_type == 'new_comment_in_huddle':
            update = update
        elif update.update_type == 'new_attendee':
            update = update
        elif update.update_type == 'new_vote':
            update = update
        elif update.update_type == 'event_reminder':
            update = update
        elif update.update_type == 'new_item':
            update.parent_text = update.item.meta.links['microcosm']['title']
            update.parent_link = update.item.meta.links['microcosm']['href']

        return update

    @classmethod
    def from_summary(cls, data):
        return Update.from_api_response(data)

    @staticmethod
    def retrieve(host, update_id, access_token):
        url = build_url(host, [Update.api_path_fragment, update_id])
        return Update.from_api_response(APIResource.retrieve(url, {}, APIResource.make_request_headers(access_token)))

    def update(self, host, access_token):
        """
        Update an Update with a 'viewed' time to indicate it has been read by the user.
        """

        url = build_url(host, [Update.api_path_fragment, self.id])
        payload = json.dumps(self.as_dict(update=True), cls=DateTimeEncoder)
        response = APIResource.update(url, payload, headers=APIResource.make_request_headers(access_token))
        return Update.from_api_response(response)

    @staticmethod
    def mark_viewed(host, update_id, access_token):
        url = build_url(host, [Update.api_path_fragment, update_id])
        payload = json.dumps([{
            'op': 'replace',
            'path': '/viewed',
            # TODO: The rare hack, seen in the wild
            'value': datetime.datetime.now().isoformat('T') + 'Z'
        }])
        headers = APIResource.make_request_headers(access_token)
        headers['Content-Type'] = 'application/json'
        requests.patch(url, payload, headers=headers)

    def as_dict(self):
        repr = {}
        repr['id'] = self.id
        repr['updateType'] = self.update_type_id
        repr['itemId'] = self.item_id
        repr['itemType'] = self.item_type
        repr['profileId'] = self.profile_id
        repr['data'] = self.data
        repr['created'] = self.created
        repr['viewed'] = self.viewed
        return repr


class UpdatePreference(APIResource):

    api_path_fragment = ['updates', 'preferences']

    @classmethod
    def from_api_response(cls, data):
        update_pref = cls()
        update_pref.profile_id = data['profileId']
        update_pref.description = data['description']
        update_pref.id = data['id']
        update_pref.send_email = data['sendEmail']
        update_pref.send_sms = data['sendSMS']
        return update_pref

    @staticmethod
    def from_list(data):
        list = []
        for update_preference in data:
            list.append(UpdatePreference.from_api_response(update_preference))
        list.sort(key=lambda x: x.id)
        return list

    @staticmethod
    def build_request(host, access_token):
        url = build_url(host, UpdatePreference.api_path_fragment)
        params = {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, access_token):
        url, params, headers = UpdatePreference.build_request(host, access_token)
        response = APIResource.process_response(url, params, headers)
        return UpdatePreference.from_list(response)

    @staticmethod
    def update(host, update_type_id, data, access_token):
        url = build_url(host, UpdatePreference.api_path_fragment + [update_type_id])
        resource = APIResource.update(url, json.dumps(data), {}, APIResource.make_request_headers(access_token))
        return UpdatePreference.from_api_response(resource)

    def as_dict(self):
        repr = {}
        repr['id'] = self.id
        repr['description'] = self.description
        repr['sendEmail'] = self.send_email
        repr['sendSMS'] = self.send_sms
        return repr


class GlobalOptions(APIResource):

    api_path_fragment = ['profiles', 'options']

    @classmethod
    def from_api_response(cls, data):
        glob_opt = cls()
        glob_opt.profile_id = data['profileId']
        glob_opt.emailNotifications = data['sendEmail']
        glob_opt.smsNotifications = data['sendSMS']
        return glob_opt

    @staticmethod
    def build_request(host, access_token):
        url = build_url(host, GlobalOptions.api_path_fragment)
        params = {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def update(host, data, access_token):
        url = build_url(host, GlobalOptions.api_path_fragment)
        resource = APIResource.update(url, json.dumps(data), {}, APIResource.make_request_headers(access_token))
        return GlobalOptions.from_api_response(resource)

    def as_dict(self):
        repr = {}
        repr['sendEmail'] = self.emailNotifications
        repr['sendSMS'] = self.smsNotifications
        return repr


class Conversation(APIResource):
    """
    Represents a conversation (title and list of comments).
    """

    api_path_fragment = 'conversations'

    @classmethod
    def from_api_response(cls, data):
        conversation = cls.from_summary(data)
        conversation.comments = PaginatedList(data['comments'], Comment)
        return conversation

    @classmethod
    def from_summary(cls, data):
        conversation = cls()
        conversation.id = data['id']
        conversation.microcosm_id = data['microcosmId']
        conversation.title = data['title']
        if data.get('lastCommentId'): conversation.last_comment_id = data['lastCommentId']
        if data.get('lastCommentCreatedBy'):
            conversation.last_comment_created_by = Profile(data['lastCommentCreatedBy'])
        if data.get('lastCommentCreated'):
            conversation.last_comment_created = parse_timestamp(data['lastCommentCreated'])
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
    def build_request(host, id, offset=None, access_token=None):
        url = build_url(host, [Conversation.api_path_fragment, id])
        params = {'offset': offset} if offset else {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, id, offset=None, access_token=None):
        url, params, headers = Conversation.build_request(host, id, offset, access_token)
        resource = APIResource.retrieve(url, params, headers)
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

    @staticmethod
    def newest(host, id, access_token=None):
        url = build_url(host, [Conversation.api_path_fragment, id, "newcomment"])
        response = requests.get(url, params={}, headers=APIResource.make_request_headers(access_token))
        return response.json()['data']

    def as_dict(self, update=False):
        repr = {}
        if update:
            repr['id'] = self.id
            repr['meta'] = self.meta
        repr['microcosmId'] = self.microcosm_id
        repr['title'] = self.title
        return repr


class Huddle(APIResource):
    """
    Represents a huddle (title and list of comments).
    """

    api_path_fragment = 'huddles'

    @classmethod
    def from_api_response(cls, data):
        huddle = cls.from_summary(data)
        huddle.comments = PaginatedList(data['comments'], Comment)
        return huddle

    @classmethod
    def from_summary(cls, data):
        huddle = cls()
        huddle.id = data['id']
        huddle.title = data['title']
        if data.get('lastCommentId'): huddle.last_comment_id = data['lastCommentId']
        if data.get('lastCommentCreatedBy'):
            huddle.last_comment_created_by = Profile(data['lastCommentCreatedBy'])
        if data.get('lastCommentCreated'):
            huddle.last_comment_created = parse_timestamp(data['lastCommentCreated'])
        if data.get('totalComments'):
            huddle.total_comments = data['totalComments']
        huddle.meta = Meta(data['meta'])
        huddle.participants = []
        for p in data['participants']:
            huddle.participants.append(Profile(p))
        return huddle

    @classmethod
    def from_create_form(cls, data):
        huddle = cls()
        huddle.title = data['title']
        return huddle

    @classmethod
    def from_edit_form(cls, data):
        huddle = Huddle.from_create_form(data)
        huddle.id = data['id']
        huddle.meta = {'editReason': data['editReason']}
        return huddle

    @staticmethod
    def build_request(host, id, offset=None, access_token=None):
        url = build_url(host, [Huddle.api_path_fragment, id])
        params = {'offset': offset} if offset else {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, id, offset=None, access_token=None):
        url, params, headers = Huddle.build_request(host, id, offset, access_token)
        resource = APIResource.retrieve(url, params, headers)
        return Huddle.from_api_response(resource)

    def create(self, host, access_token):
        url = build_url(host, [Huddle.api_path_fragment])
        payload = json.dumps(self.as_dict(), cls=DateTimeEncoder)
        resource = APIResource.create(url, payload, {}, APIResource.make_request_headers(access_token))
        return Huddle.from_api_response(resource)

    def delete(self, host, access_token):
        url = build_url(host, [Huddle.api_path_fragment, self.id])
        APIResource.delete(url, {}, APIResource.make_request_headers(access_token))

    @staticmethod
    def newest(host, id, access_token=None):
        url = build_url(host, [Huddle.api_path_fragment, id, "newcomment"])
        response = requests.get(url, params={}, headers=APIResource.make_request_headers(access_token))
        return response.json()['data']

    def as_dict(self, update=False):
        repr = {}
        if update:
            repr['id'] = self.id
            repr['meta'] = self.meta
        repr['title'] = self.title
        return repr

    @staticmethod
    def invite(host, id, profileIds, access_token=None):
        url = build_url(host, [Huddle.api_path_fragment, id, "participants"])
        payload = []
        for pid in profileIds:
            payload.append({'id': pid})
        resource = APIResource.update(url, json.dumps(payload), {}, APIResource.make_request_headers(access_token))
        return Huddle.from_api_response(resource)

class HuddleList(object):
    """
    Represents a list of microcosms for a given site.
    """

    api_path_fragment = 'huddles'

    def __init__(self, data):
        self.huddles = PaginatedList(data['huddles'], Huddle)
        self.meta = Meta(data['meta'])

    @staticmethod
    def build_request(host, offset=None, access_token=None):
        url = build_url(host, [HuddleList.api_path_fragment])
        params = {'offset': offset} if offset else {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, offset=None, access_token=None):
        url, params, headers = HuddleList.build_request(host, offset, access_token)
        resource = APIResource.retrieve(url, params, headers)
        return HuddleList(resource)


class Event(APIResource):
    """
    Represents an event (event details and list of comments).
    """

    api_path_fragment = 'events'

    @classmethod
    def from_api_response(cls, data):
        event = cls.from_summary(data)
        event.comments = PaginatedList(data['comments'], Comment)
        event.when = parse_timestamp(data['when'])
        event.duration = data['duration']
        event.status = data['status']

        return event

    @classmethod
    def from_summary(cls, data):
        event = cls()
        event.id = data['id']
        event.microcosm_id = data['microcosmId']
        event.title = data['title']
        if data.get('lastCommentId'): event.last_comment_id = data['lastCommentId']
        if data.get('lastCommentCreatedBy'):
            event.last_comment_created_by = Profile(data['lastCommentCreatedBy'])
        if data.get('lastCommentCreated'):
            event.last_comment_created = parse_timestamp(data['lastCommentCreated'])
        event.meta = Meta(data['meta'])

        # RSVP attend / spaces are only returned if non-zero
        if data.get('rsvpAttend'): event.rsvp_attend = data['rsvpAttend']
        if data.get('rsvpSpaces'): event.rsvp_spaces = data['rsvpSpaces']

        # RSVP limit is always returned, even if zero
        event.rsvp_limit = data['rsvpLimit']

        if data.get('when'): event.when = parse_timestamp(data['when'])
        if data.get('where'): event.where = data['where']
        if data.get('lat'): event.lat = data['lat']
        if data.get('lon'): event.lon = data['lon']
        if data.get('north'): event.north = data['north']
        if data.get('east'): event.east = data['east']
        if data.get('south'): event.south = data['south']
        if data.get('west'): event.west = data['west']
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
    def build_request(host, id, offset=None, access_token=None):
        url = build_url(host, [Event.api_path_fragment, id])
        params = {'offset': offset} if offset else {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, id, offset=None, access_token=None):
        url, params, headers = Event.build_request(host, id, offset, access_token)
        resource = APIResource.retrieve(url, params, headers)
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

    @staticmethod
    def newest(host, id, access_token=None):
        url = build_url(host, [Event.api_path_fragment, id, "newcomment"])
        response = requests.get(url, params={}, headers=APIResource.make_request_headers(access_token))
        return response.json()['data']

    @staticmethod
    def build_attendees_request(host, id, access_token=None):
        url = build_url(host, [Event.api_path_fragment, id, 'attendees'])
        params = {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    def get_attendees(self, host, access_token=None):
        """
        Retrieve a list of attendees for an event.
        TODO: pagination support
        """

        url, params, headers = self.build_attendees_request(host, access_token)
        resource = APIResource.retrieve(url, params, headers)
        return AttendeeList(resource)

    @classmethod
    def rsvp(cls, host, event_id, profile_id, attendance_data, access_token):
        """
        Create or update attendance to an event.
        TODO: This is obviously pretty nasty but it'll be changed when PATCH support is added.
        """

        collection_url = build_url(host, [cls.api_path_fragment, event_id, 'attendees'])

        # If it is not found, POST an attendance
        try:
            resource = APIResource.update(collection_url, json.dumps(attendance_data), {'access_token': access_token}, {})
            print json.dumps(attendance_data)
        except RequestException:
            raise
        return Event.from_api_response(resource)


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
        attendee.profile_id = data['profileId']
        attendee.profile = Profile.from_summary(data['profile'])
        attendee.rsvp = data['rsvp']
        attendee.rsvpd_on = data['rsvpdOn']
        attendee.meta = Meta(data['meta'])
        return attendee


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
        if data.get('inReplyTo'):
            comment.in_reply_to = data['inReplyTo']
        if data.get('attachments'):
            comment.attachments = data['attachments']
        if data.get('firstLine'):
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
    def build_request(host, id, offset=None, access_token=None):
        url = build_url(host, [Comment.api_path_fragment, id])
        params = {'offset': offset} if offset else {}
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers

    @staticmethod
    def retrieve(host, id, offset=None, access_token=None):
        url, params, headers = Comment.build_request(host, id, offset, access_token)
        resource = APIResource.retrieve(url, params, headers)
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

    @staticmethod
    def incontext(host, id, access_token=None):
        url = build_url(host, [Comment.api_path_fragment, id, "incontext"])
        response = requests.get(url, params={}, headers=APIResource.make_request_headers(access_token))
        return response.json()['data']

    @staticmethod
    def source(host, id, access_token=None):
        url = build_url(host, [Comment.api_path_fragment, id])
        response = requests.get(url, params={}, headers=APIResource.make_request_headers(access_token))
        return response.content


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

class Search(object):
    """
    Used for searching and search results
    """

    api_path_fragment = "search"

    @classmethod
    def from_api_response(cls, data):
        search = cls()
        search.query = data['query']
        search.type = []
        if data['query'].get('type'):
            for t in data['query']['type']:
                search.type.append(t)
        search.time_elapsed = data['timeTakenInMs']/float(1000)
        search.results = PaginatedList(data['results'], SearchResult)
        return search

    @staticmethod
    def build_request(host, params=None, access_token=None):
        url = build_url(host, [Search.api_path_fragment])
        headers = APIResource.make_request_headers(access_token)
        return url, params, headers


class SearchResult(object):
    """
    The search result object
    """

    @classmethod
    def from_api_response(cls, data):
        searchresult = cls()
        searchresult.item_type = data['itemType']

        searchresult.item = populate_item(searchresult.item_type, data['item'])

        if data.get('parentItem'):
            searchresult.parent_item_type = data['parentItemType']
            searchresult.parent_item = populate_item(searchresult.parent_item_type, data['parentItem'])

        searchresult.rank = data['rank']
        searchresult.last_modified = data['lastModified']
        searchresult.highlight = data['highlight']
        return searchresult

    @classmethod
    def from_summary(cls, data):
        return SearchResult.from_api_response(data)
