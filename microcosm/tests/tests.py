import random
import string
import json
import os
from mock import patch

from django.utils import unittest
from django.test.client import RequestFactory

from microcosm.views import MicrocosmView
from microcosm.views import build_pagination_links

from microcosm.api.resources import Conversation
from microcosm.api.resources import Microcosm
from microcosm.api.resources import MicrocosmList
from microcosm.api.resources import Profile
from microcosm.api.resources import Site
from microcosm.api.resources import Event

from microweb.helpers import build_url

from microweb.settings import API_SCHEME
from microweb.settings import API_DOMAIN_NAME
from microweb.settings import API_PATH
from microweb.settings import API_VERSION

TEST_ROOT = os.path.dirname(os.path.abspath(__file__))


def generate_location():
    # Construct a random subdomain string
    subdomain = ''
    for x in xrange(10):
        subdomain += random.choice(string.lowercase)
    return '%s.microco.sm' % subdomain


class BuildURLTests(unittest.TestCase):
    """
    Verify that helpers.build_url() builds valid URLs.
    """

    subdomain_key = 'abc.'

    def testWithTrailingSeparator(self):
        url = build_url((BuildURLTests.subdomain_key + API_DOMAIN_NAME), ['resource/', '1/', 'extra/'])
        assert url == API_SCHEME + BuildURLTests.subdomain_key + \
                      API_DOMAIN_NAME + '/' + API_PATH + '/' + API_VERSION + '/resource/1/extra'

    def testWithPrependedSeparator(self):
        url = build_url((BuildURLTests.subdomain_key + API_DOMAIN_NAME), ['/resource', '/1', '/extra'])
        assert url == API_SCHEME + BuildURLTests.subdomain_key + \
                      API_DOMAIN_NAME + '/' + API_PATH + '/' + API_VERSION + '/resource/1/extra'

    def testWithDuplicateSeparator(self):
        url = build_url((BuildURLTests.subdomain_key + API_DOMAIN_NAME), ['resource/', '/1/', '/extra/'])
        assert url == API_SCHEME + BuildURLTests.subdomain_key + \
                      API_DOMAIN_NAME + '/' + API_PATH + '/' + API_VERSION + '/resource/1/extra'

    def testWithNoSeparator(self):
        url = build_url((BuildURLTests.subdomain_key + API_DOMAIN_NAME), ['resource', '1', 'extra'])
        assert url == API_SCHEME + BuildURLTests.subdomain_key + \
                      API_DOMAIN_NAME + '/' + API_PATH + '/' + API_VERSION + '/resource/1/extra'

    def testEmptyFragments(self):
        url = build_url((BuildURLTests.subdomain_key + API_DOMAIN_NAME), [])
        assert url == API_SCHEME + BuildURLTests.subdomain_key + \
                      API_DOMAIN_NAME + '/' + API_PATH + '/' + API_VERSION

    def testIntFragment(self):
        url = build_url((BuildURLTests.subdomain_key + API_DOMAIN_NAME), [1, 2, 3])
        assert url == API_SCHEME + BuildURLTests.subdomain_key + \
                      API_DOMAIN_NAME + '/' + API_PATH + '/' + API_VERSION + '/1/2/3'

    def testInvalidFragment(self):
        with self.assertRaises(AssertionError):
            build_url((BuildURLTests.subdomain_key + API_DOMAIN_NAME), ['resource', '1', 'ex/tra'])

    def testFailCustomDomains(self):
        with self.assertRaises(AssertionError):
            build_url((BuildURLTests.subdomain_key + 'example.org'), ['resource', '1', 'ex/tra'])


class RoutingAPITests(unittest.TestCase):
    """
    Verify that the Host header is used to call the appropriate
    API endpoint.
    """

    def setUp(self):
        self.factory = RequestFactory()


    def testMicrocosmsView(self):

        host = generate_location()
        full_path = build_url(host, ['microcosms'])

        # Create a request for a list of microcosms
        request = self.factory.get('/microcosms', HTTP_HOST=host)
        request.access_token = None
        request.whoami = None
        request.site = None

        microcosms = json.loads(open(os.path.join(TEST_ROOT, 'data', 'microcosms.json')).read())

        # Patch requests.get and check the call args
        with patch('requests.get') as mock:
            mock.return_value.json.return_value = microcosms
            MicrocosmView.list(request)
            mock.assert_called_once_with(full_path, headers={'Host': host}, params={})


class PaginationTests(unittest.TestCase):
    """
    Verify that pagination nav links are built correctly for all pages
    where pagination can occur.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def testLinks(self):
        """
        Assert that a response containing a 'next page' link is correctly represnted in navigation.
        """

        host = generate_location()
        path = '/conversations/1'
        # Create a request for a list of microcosms
        request = self.factory.get(path, HTTP_HOST=host)
        request.access_token = None
        request.whoami = None
        request.site = None

        conversation = Conversation.from_api_response(json.loads(open(os.path.join(TEST_ROOT, 'data', 'conversation.json')).read())['data'])
        with patch('requests.get') as mock:
            mock.return_value.json.return_value = conversation
            pagination_nav = build_pagination_links(request, conversation.comments)

        assert pagination_nav['first'] == path
        assert pagination_nav['prev'] == path + '?offset=25'
        assert pagination_nav['next'] == path + '?offset=75'
        assert pagination_nav['last'] == path + '?offset=100'


class ResourceTests(unittest.TestCase):

    """
    Basic initialisation and serilisation tests for API resources.
    """

    def testMicrocosmInit(self):
        Microcosm(json.loads(open(os.path.join(TEST_ROOT, 'data', 'microcosm.json')).read())['data'])

    def testMicrocosmAsDict(self):
        microcosm = Microcosm(json.loads(open(os.path.join(TEST_ROOT, 'data', 'microcosm.json')).read())['data'])
        microcosm.as_dict

    def testMicrocosmSummaryInit(self):
        Microcosm(json.loads(open(os.path.join(TEST_ROOT, 'data', 'microcosm.json')).read())['data'], summary=True)

    def testMicrocosmListInit(self):
        MicrocosmList(json.loads(open(os.path.join(TEST_ROOT, 'data', 'microcosms.json')).read())['data'])

    def testConversationInit(self):
        Conversation.from_api_response(json.loads(open(os.path.join(TEST_ROOT, 'data', 'conversation.json')).read())['data'])

    def testConversationAsDict(self):
        conversation = Conversation.from_api_response(json.loads(open(os.path.join(TEST_ROOT, 'data', 'conversation.json')).read())['data'])
        conversation.as_dict()

    def testEventInit(self):
        Event.from_api_response(json.loads(open(os.path.join(TEST_ROOT, 'data', 'event.json')).read())['data'])

    def testEventAsDict(self):
        event = Event.from_api_response(json.loads(open(os.path.join(TEST_ROOT, 'data', 'event.json')).read())['data'])
        event.as_dict()

    def testProfileInit(self):
        Profile(json.loads(open(os.path.join(TEST_ROOT, 'data', 'profile.json')).read())['data'])

    def testProfileAsDict(self):
        profile = Profile(json.loads(open(os.path.join(TEST_ROOT, 'data', 'profile.json')).read())['data'])
        profile.as_dict

    def testProfileSummaryInit(self):
        Profile(json.loads(open(os.path.join(TEST_ROOT, 'data', 'profile.json')).read())['data'], summary=True)

    def testSiteInit(self):
        Site(json.loads(open(os.path.join(TEST_ROOT, 'data', 'site.json')).read())['data'])
