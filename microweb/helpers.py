import datetime
import json
import re

# A hack used when converting timestamp strings to datetime.datetime instances
VALID_DATETIME = re.compile(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}.?\d{0,6}Z$')

def build_url(authority, path=None):
    """
    urljoin and os.path.join don't behave exactly as we want, so
    here's a different wheel.

    As per RFC 3986, authority is composed of hostname[:port] (and optionally
    userinfo, but the microcosm API will never accept these in the URL, so
    we ignore them).

    path should be a list of fragments. This function will strip slashes and
    insert them where needed to form a valid URL.

    The use of += for string concat is deemed acceptable because it is 'fast enough'
    on CPython and we are not going to change interpreter.
    """

    for fragment in path:
        if '/' in fragment:
            stripped = path[fragment].strip('/')
        if '/' in stripped:
            raise AssertionError('Do not use path fragments containing slashes')
        authority += ('/' + stripped)

    return authority


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime.datetime objects, producing an
    ISO 8601-formatted string.
    """

    def default(self, object):
        if isinstance(object, datetime.datetime):
            return object.isoformat()
        else:
            return super(DateTimeEncoder, self).default(object)
