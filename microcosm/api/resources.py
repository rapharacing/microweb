import json
from urlparse import urljoin
from dateutil.parser import parse as parse_timestamp
import requests
from requests import RequestException
from microcosm.api.exceptions import APIException
from microweb.helpers import DateTimeEncoder, VALID_DATETIME
from microweb.settings import API_ROOT


class APIResource(object):
    """
    Base API resource that performs HTTP operations. Each API class should subclass this
    to deal with custom validation and JSON processing.
    """

    @classmethod
    def retrieve(cls, id=None, offset=None, access_token=None, url_override=None):
        """
        GET an API resource. If resource ID is omitted, returns a list. Appends access_token
        and offset (for paging) if provided.
        """

        if url_override:
            resource_url = url_override
        else:
            resource_url = urljoin(API_ROOT, cls.resource_fragment)

        params = {}
        if access_token:
            params['access_token'] = access_token

        if offset:
            offset = int(offset)
            assert offset % 25 == 0, 'Offset must be a multiple of 25'
            params['offset'] = offset

        if id and not url_override:
            id = int(id)
            assert id > 0, 'Resource ID must be greater than zero'
            resource_url += '/%d' % id

        response = requests.get(resource_url, params=params)

        try:
            resource = response.json()
        except ValueError:
            raise APIException('The API has returned invalid json', 500)

        if resource['error']:
            raise APIException(resource['error'], response.status_code)

        if not resource['data']:
            raise APIException('No data returned at: %s' % resource_url)

        return resource['data']

    @classmethod
    def create(cls, data, access_token=None, headers=None):
        """
        Create an API resource with POST.
        """

        resource_url = urljoin(API_ROOT, cls.resource_fragment)

        params = {}
        if access_token:
            params['access_token'] = access_token

        if headers:
            headers['Content-Type'] = 'application/json'
        else:
            headers = {'Content-Type': 'application/json'}

        response = requests.post(
            resource_url,
            data=json.dumps(data, cls=DateTimeEncoder),
            headers=headers,
            params=params
        )

        try:
            resource = response.json()
        except ValueError:
            raise APIException('The API has returned invalid json', 500)

        if resource['error']:
            raise APIException(resource['error'], response.status_code)

        if not resource['data']:
            raise APIException('No data returned at: %s' % resource_url)

        return resource['data']

    @classmethod
    def update(cls, data, id, access_token):
        """
        Update an API resource with PUT.
        """

        resource_url = urljoin(API_ROOT, cls.resource_fragment)
        headers = {'Content-Type': 'application/json'}
        params = {'method' : 'PUT'}

        if access_token:
            params['access_token'] = access_token

        id = int(id)
        assert id > 0, 'Resource ID must be greater than zero'
        resource_url += '/%d' % id

        response = requests.post(
            resource_url,
            data=json.dumps(data, cls=DateTimeEncoder),
            headers=headers,
            params=params
        )

        try:
            resource = response.json()
        except ValueError:
            raise APIException('The API has returned invalid json', 500)

        if resource['error']:
            raise APIException(resource['error'], response.status_code)

        if not resource['data']:
            raise APIException('No data returned at: %s' % resource_url)

        return resource['data']

    @classmethod
    def delete(cls, id, access_token):
        """
        DELETE an API resource. ID must be supplied.

        A 'data' object is never returned by a DELETE, so this
        method will raise an exception on failure. In normal
        operation the method simply returns.
        """

        resource_url = urljoin(API_ROOT, cls.resource_fragment)
        params = {
            'method': 'DELETE',
            'access_token': access_token,
        }

        if id:
            id = int(id)
            assert id > 0, 'Resource ID must be greater than zero'
            resource_url += '/%d' % id
        elif access_token:
            resource_url += '/%s' % access_token
        else:
            raise AssertionError, 'You must supply either an id or '\
                                  'an access_token to delete'

        response = requests.post(resource_url, params=params)

        try:
            resource = response.json()
        except ValueError:
            raise APIException('The API has returned invalid json', 500)

        if resource['error']:
            raise APIException(resource['error'], response.status_code)

    @staticmethod
    def process_timestamp(resource):
        """
        Recurse over unmarshalled json and convert
        any strings that are ISO8601-like into python
        datetime objects. This is far from ideal and will be replaced
        in future with xpath-like notation for visiting specific
        attributes.

        Args:
            resource: an JSON API response that has been deserialized. This will
            usually be a dictionary but could also be a list.

        Returns:
            the same resource, but with timestamp strings as datetime objects.
        """

        if isinstance(resource, list):
            for item in resource:
                APIResource.process_timestamp(item)
        else:
            for key in resource.keys():
                if isinstance(resource[key], unicode):
                    if bool(VALID_DATETIME.search(str(resource[key]))):
                        resource[key] = parse_timestamp(resource[key])
                elif isinstance(resource[key], list) or isinstance(resource[key], dict):
                    APIResource.process_timestamp(resource[key])
            return resource

    @classmethod
    def create_linkmap(cls, resource):
        """
        Mutate a list of links into a dictionary for easy access
        in templates. This will stop working if 'href' attributes
        are returned as a list as per spec.
        """

        # Applies to all resources
        if resource.has_key('meta') and resource['meta'].get('links', None):
            resource['meta']['linkmap'] = APIResource.list_to_map(resource['meta']['links'])

        inner_list = None
        # Applies only to single items
        if resource.has_key('id'):
            if resource.get('comments', None):
                inner_list = resource['comments']
            elif resource.get('items', None):
                inner_list = resource['items']
        # Applies to collections
        elif resource.get(cls.resource_fragment, None):
            inner_list = resource[cls.resource_fragment]

        # Transform the outer 'links' array, and the links array on every list item
        if inner_list:
            if inner_list.get('links', None):
                inner_list['linkmap'] = APIResource.list_to_map(inner_list['links'])

            if inner_list['items']:
                for item in inner_list['items']:
                    if item.has_key('meta') and item['meta'].has_key('links'):
                        item['meta']['linkmap'] = APIResource.list_to_map(item['meta']['links'])

        return resource

    @staticmethod
    def list_to_map(links):
        linkmap = {}
        for link in links:
            linkmap[link['rel']]= link['href']
        return linkmap


class Site(APIResource):
    resource_fragment = 'site'

    @classmethod
    def retrieve(cls):
        resource = super(Site, cls).retrieve()
        return APIResource.process_timestamp(resource)


class User(APIResource):
    resource_fragment = 'users'


class Authentication(APIResource):
    resource_fragment = 'auth'


class WhoAmI(APIResource):
    resource_fragment = 'whoami'

    @classmethod
    def retrieve(cls, access_token):
        resource = super(WhoAmI, cls).retrieve(access_token=access_token)
        resource = cls.create_linkmap(resource)
        return APIResource.process_timestamp(resource)


class Profile(APIResource):
    resource_fragment = 'profiles'

    @classmethod
    def retrieve(cls, id, offset=None, access_token=None):
        resource = super(Profile, cls).retrieve(id, access_token=access_token)
        resource = cls.create_linkmap(resource)
        return APIResource.process_timestamp(resource)


class Microcosm(APIResource):
    resource_fragment = 'microcosms'

    @classmethod
    def retrieve(cls, id=None, offset=None, access_token=None):
        resource = super(Microcosm, cls).retrieve(id, offset, access_token)
        resource = cls.create_linkmap(resource)
        return APIResource.process_timestamp(resource)


class Conversation(APIResource):
    resource_fragment = 'conversations'

    @classmethod
    def retrieve(cls, id=None, offset=None, access_token=None):
        resource = super(Conversation, cls).retrieve(id, offset, access_token)
        resource = cls.create_linkmap(resource)
        return APIResource.process_timestamp(resource)


class Event(APIResource):
    resource_fragment = 'events'

    @classmethod
    def retrieve(cls, id=None, offset=None, access_token=None):
        resource = super(Event, cls).retrieve(id, offset, access_token)
        resource = cls.create_linkmap(resource)
        return APIResource.process_timestamp(resource)

    @classmethod
    def retrieve_attendees(cls, id, access_token=None):
        """
        Retrieve a list of attendees for an event.
        TODO: pagination support
        """

        resource_url = urljoin(API_ROOT, cls.resource_fragment) + ''.join(['/', id, '/attendees'])
        resource = APIResource.retrieve(id=id, access_token=access_token, url_override=resource_url)
        resource = cls.create_linkmap(resource)
        return APIResource.process_timestamp(resource)

    @classmethod
    def rsvp(cls, event_id, profile_id, attendance_data, access_token):
        """
        Create or update attendance to an event.
        TODO: This is obviously pretty nasty but it'll be changed soon.
        """

        collection_url = urljoin(API_ROOT, cls.resource_fragment) + \
                       ''.join(['/', event_id, '/attendees'])
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
    def retrieve(cls, id=None, offset=None, access_token=None):
        resource = super(Poll, cls).retrieve(id, offset, access_token)
        resource = cls.create_linkmap(resource)
        return APIResource.process_timestamp(resource)


class Comment(APIResource):
    resource_fragment = 'comments'

    @classmethod
    def retrieve(cls, id=None, offset=None, access_token=None):
        resource = super(Comment, cls).retrieve(id, offset, access_token)
        resource = cls.create_linkmap(resource)
        return APIResource.process_timestamp(resource)


class GeoCode():
    """
    This is simply request proxying, so don't attempt formatting
    or error recovery.
    """

    @classmethod
    def retrieve(cls, q, access_token):
        """
        Forward a geocode request (q) to the API.
        """
        params = {'q': q}
        headers = {'Authorization': 'Bearer %s' % access_token}
        response = requests.get(API_ROOT + 'geocode', params=params, headers=headers)
        return response.content
