import random
import string
import json
import os

from django.utils import unittest
from django.conf import settings
from django.test.client import RequestFactory

from mock import patch

from microcosm.views import MicrocosmView
from microcosm.views import build_pagination_links

from microcosm.api.resources import Conversation
from microcosm.api.resources import Microcosm
from microcosm.api.resources import MicrocosmList
from microcosm.api.resources import Profile
from microcosm.api.resources import Site
from microcosm.api.resources import Event
from microcosm.api.resources import build_url

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
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), ['resource/', '1/', 'extra/'])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION + '/resource/1/extra'

    def testWithPrependedSeparator(self):
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), ['/resource', '/1', '/extra'])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION + '/resource/1/extra'

    def testWithDuplicateSeparator(self):
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), ['resource/', '/1/', '/extra/'])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION + '/resource/1/extra'

    def testWithNoSeparator(self):
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), ['resource', '1', 'extra'])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION + '/resource/1/extra'

    def testEmptyFragments(self):
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), [])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION

    def testIntFragment(self):
        url = build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), [1, 2, 3])
        assert url == settings.API_SCHEME + BuildURLTests.subdomain_key +\
                      settings.API_DOMAIN_NAME + '/' + settings.API_PATH + '/' + settings.API_VERSION + '/1/2/3'

    def testInvalidFragment(self):
        with self.assertRaises(AssertionError):
            build_url((BuildURLTests.subdomain_key + settings.API_DOMAIN_NAME), ['resource', '1', 'ex/tra'])

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
    Basic initialisation and serialisation tests for API resources.
    TODO: in some cases, as_dict is a property, in others it is a callable.
    """

    def testMicrocosmInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'microcosm.json')).read())['data']
        Microcosm.from_api_response(data)

    def testMicrocosmAsDict(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'microcosm.json')).read())['data']
        microcosm = Microcosm.from_api_response(data)
        microcosm.as_dict

    def testMicrocosmSummaryInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'microcosm.json')).read())['data']
        Microcosm.from_summary(data)

    def testConversationInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'conversation_with_comment.json')).read())['data']
        Conversation.from_api_response(data)

    def testCommentedConversationInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'conversation_without_comment.json')).read())['data']
        Conversation.from_api_response(data)

    def testConversationAsDict(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'conversation_without_comment.json')).read())['data']
        conversation = Conversation.from_api_response(data)
        conversation.as_dict()

    def testEventInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'event_without_comment.json')).read())['data']
        Event.from_api_response(data)

    def testCommentedEventInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'event_with_comment.json')).read())['data']
        Event.from_api_response(data)

    def testEventAsDict(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'event_without_comment.json')).read())['data']
        event = Event.from_api_response(data)
        event.as_dict()

    def testWhoamiInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'whoami.json')).read())['data']
        Profile(data)

    def testProfileInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'profile.json')).read())['data']
        Profile(data)

    def testProfileAsDict(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'profile.json')).read())['data']
        profile = Profile(data)
        profile.as_dict

    def testProfileSummaryInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'profile.json')).read())['data']
        Profile(data, summary=True)

    def testSiteInit(self):
        data = json.loads(open(os.path.join(TEST_ROOT, 'data', 'site.json')).read())['data']
        Site(data)
