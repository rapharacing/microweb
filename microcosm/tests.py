import random
import string
import datetime
from mock import patch

from django.utils import unittest
from django.test.client import RequestFactory

from microcosm.views import MicrocosmView, ConversationView
from microweb.helpers import build_url

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


class PaginationTests(unittest.TestCase):
    """
    Verify that pagination nav links are built correctly for all pages
    where pagination can occur.
    """

    def testConversationPagination(self):

        # TODO: read resources from a file, remove hardcoded values
        resource = {
            'id': 1,
            'comments': {
                'maxOffset': 75, # indicating 4 pages of comments
                'linkmap': {
                    'first': 'first',
                    'prev': 'prev',
                    'next': 'next',
                    'last': 'last',
                }
            }
        }

        view_data = {
            'pagination': {}
        }
        # current offset of 50, so viewing page 3
        ConversationView.build_pagination_nav('path', resource, view_data, 50)

        assert view_data['pagination']['first'] == 'path'
        assert view_data['pagination']['last'] == 'path?offset=75'
        assert view_data['pagination']['next'] == 'path?offset=75'
        assert view_data['pagination']['prev'] == 'path?offset=25'

