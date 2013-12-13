import datetime
import json

from settings import API_VERSION
from settings import API_PATH
from settings import API_SCHEME
from settings import API_DOMAIN_NAME

CNAMED_HOST_MAPPINGS = {
    'forum.espruino.com': 'espruino.microco.sm',
    'forum.pixelcharter.com': 'sandbox.microco.sm',
    'www.bowlie.com': 'bowlie.microco.sm',
}

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

    if host.endswith(API_DOMAIN_NAME):
        url = API_SCHEME + host
    else:
        # Host does not end with API_DOMAIN_NAME, so it's a CNAME.
        # In future this will use the sites management API and
        # synchronize a cache of CNAMEd sites.
        if CNAMED_HOST_MAPPINGS.has_key(host):
            url = API_SCHEME + CNAMED_HOST_MAPPINGS[host]
        else:
            raise AssertionError('Unknown CNAMEd host: %s' % host)

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

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime.datetime objects, producing an
    ISO 8601-formatted string.
    """

    def default(self, object):
        if isinstance(object, datetime.datetime):
            return object.isoformat()
        else:
            return super(DateTimeEncoder, self).default(object)
