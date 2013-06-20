import datetime
import json
import re

from settings import API_VERSION
from settings import API_PATH
from settings import API_SCHEME
from settings import API_DOMAIN_NAME

# A hack used when converting timestamp strings to datetime.datetime instances
VALID_DATETIME = re.compile(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}.?\d{0,6}Z$')

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

    if not host.endswith(API_DOMAIN_NAME):
        raise AssertionError('Custom domains are not yet supported on Microcosm')

    url = API_SCHEME + host
    path_fragments = [API_PATH, API_VERSION] + path_fragments

    for fragment in path_fragments:
        if not isinstance(fragment, str):
            fragment = str(fragment)
        if '/' in fragment:
            fragment = fragment.strip('/')
            if '/' in fragment:
                raise AssertionError('Do not use path fragments containing slashes')
        url += ('/' + fragment)

    return url


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime.datetime objects, producing an
    ISO 8601-formatted string.
    """

    def default(self, object):
        if isinstance(object, datetime.datetime):
            return object.isoformat()
        else:
            return super(DateTimeEncoder, self).default(object)
