import random
import string
from mock import patch

from django.utils import unittest
from django.test.client import RequestFactory

from microcosm.views import MicrocosmView

from microweb.helpers import build_url
from microweb.settings import API_SCHEME
from microweb.settings import API_DOMAIN_NAME


class BuildURLTests(unittest.TestCase):
    """
    Verify that helpers.build_url() builds valid URLs.
    """

    def testWithTrailingSeparator(self):
        url = build_url('a.microco.sm', ['resource/', '1/', 'extra/'])
        assert url == 'https://a.microco.sm/api/v1/resource/1/extra'

    def testWithPrependedSeparator(self):
        url = build_url('a.microco.sm', ['/resource', '/1', '/extra'])
        assert url == 'https://a.microco.sm/api/v1/resource/1/extra'

    def testWithDuplicateSeparator(self):
        url = build_url('a.microco.sm', ['resource/', '/1/', '/extra/'])
        assert url == 'https://a.microco.sm/api/v1/resource/1/extra'

    def testWithNoSeparator(self):
        url = build_url('a.microco.sm', ['resource', '1', 'extra'])
        assert url == 'https://a.microco.sm/api/v1/resource/1/extra'

    def testEmptyFragments(self):
        url = build_url('a.microco.sm', [])
        assert url == 'https://a.microco.sm/api/v1'

    def testIntFragment(self):
        url = build_url('a.microco.sm', [1, 2, 3])
        assert url == 'https://a.microco.sm/api/v1/1/2/3'

    def testInvalidFragment(self):
        with self.assertRaises(AssertionError):
            build_url('a.microco.sm', ['resource', '1', 'ex/tra'])

    def testFailCustomDomains(self):
        with self.assertRaises(AssertionError):
            build_url('a.example.org', ['resource', '1', 'ex/tra'])


class RoutingAPITests(unittest.TestCase):
    """
    Verify that the Host header is used to call the appropriate
    API endpoint.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def testMicrocosmsView(self):

        # Construct a random subdomain string
        subdomain = ''
        for x in xrange(10):
            subdomain += random.choice(string.lowercase)
        host = '%s.microco.sm' % subdomain

        # Create a request for a list of microcosms
        request = self.factory.get('/microcosms', HTTP_HOST=host)
        request.access_token = None
        request.whoami = None
        request.site = None

        # Patch requests.get and check the call args
        with patch('requests.get') as mock:
            mock.return_value.json.return_value = {'error': None, 'data': {'hi': 5}}
            MicrocosmView.list(request)
            path = build_url(host, ['microcosms'])
            mock.assert_called_once_with(path, headers={'Host': host}, params={})
