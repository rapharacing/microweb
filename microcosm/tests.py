from django.utils import unittest
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