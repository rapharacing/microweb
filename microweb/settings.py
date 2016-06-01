import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Do not change these settings. Override them in local_settings.py if necessary.
DEBUG = False
TEMPLATE_DEBUG = False

# ALLOWED_HOSTS is required in >Django 1.5. Since we allow customers to CNAME their domain
# to a microcosm site, we cannot make use of this feature. Host is verified in the API.
ALLOWED_HOSTS = [
    '*',
]

# Test runner requires a database. This should never be used to store anything.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

TIME_ZONE = 'Europe/London'
LANGUAGE_CODE = 'en-gb'

# For Django sites framework, not used for anything in microcosm.
SITE_ID = 1

# Internationalisation settings.
USE_I18N = True
USE_L10N = True
USE_TZ = True

## DO NOT ENABLE THIS, it will break editing and other places that embed identifiers
## within forms.
#USE_THOUSAND_SEPARATOR = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# In production these are served by nginx.
STATIC_ROOT = '/srv/www/django/microweb/static/'

# URL prefix for static files.
STATIC_URL = '/static/'
STATICFILES_DIRS = ()
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.core.context_processors.static',
)
TEMPLATE_DIRS = ()

MIDDLEWARE_CLASSES = (
    # Note: if using messages, enable the sessions middleware too
    'django.middleware.common.CommonMiddleware',

    # CSRF protection on form submission
    'django.middleware.csrf.CsrfViewMiddleware',

    # Convenience for request context like site, user account, etc.
    'core.middleware.context.ContextMiddleware',

    # Redirect to custom domain, if one exists for the site
    'core.middleware.redirect.DomainRedirectMiddleware',

    # # Google Analytics from the server.
    #'core.middleware.ga.GAMiddleware',

    # Google Analytics proxy from the server.
    'core.middleware.isogram.IsogramMiddleware',

    # # cache busting for static files
    # 'core.middleware.modtimeurls.ModTimeUrlsMiddleware',

    # # preconnect for 3rd party assets
    # 'core.middleware.preconnect.PreconnectMiddleware',

    # # time all requests and report to riemann
    # 'core.middleware.timing.TimingMiddleware',

    # # push exceptions to riemann
    # 'core.middleware.exception.ExceptionMiddleware',
)

ROOT_URLCONF = 'microweb.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'microweb.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'core',
    'conversations',
    'events',
    'microcosms',
    'huddles',
    'comments',
    'profiles',
    'updates',
    'search',
    'trending',
    'moderation',
    'redirect',
    'gunicorn',
    'core.templatetags.comments',
    'core.templatetags.conversation',
    'core.templatetags.event',
    'core.templatetags.commentBox',
    'core.templatetags.profile',
    'core.templatetags.microcosm',
    'core.templatetags.list_comment',
    'core.templatetags.get_attachment',
    'core.templatetags.huddle',
    'core.templatetags.is_image',
)

# The values below in must be initialised in local_settings.py
# Example values can be found in local_settings.py.example

# Credentials generated when registering an application.
from local_settings import CLIENT_ID
from local_settings import CLIENT_SECRET

# Microcosm API settings.
from local_settings import API_SCHEME
from local_settings import API_DOMAIN_NAME
from local_settings import API_PATH
from local_settings import API_VERSION

if API_SCHEME == '' or API_DOMAIN_NAME == '' or API_PATH == '' or API_VERSION == '':
    raise Exception('Please define API settings in local_settings.py')

# Riemann is used for exception reporting and metrics. Can be assigned empty
# values in local_settings for local development.
from microweb.local_settings import RIEMANN_ENABLED
from microweb.local_settings import RIEMANN_HOST

# Google Analytics, server-side driven. Can be assigned empty values in
# local_settings for local development.
from microweb.local_settings import GA_ENABLED
from microweb.local_settings import GA_KEY

# Google Analytics, proxied through a local path
from microweb.local_settings import ISOGRAM_ENABLED

# Mostly used for site information cache. Compulsory.
from microweb.local_settings import MEMCACHE_HOST
from microweb.local_settings import MEMCACHE_PORT

# Page size for list views: Microcosms, Huddles, etc.
from microweb.local_settings import PAGE_SIZE

# In production, all logging goes to stdout which is redirected by gunicorn.
# This isn't ideal (we can't route to mulitple places), but works well enough.
from microweb.local_settings import LOGGING

# Make this unique, and don't share it with anybody.
from microweb.local_settings import SECRET_KEY

# Allows shadowing of DEBUG for development.
from microweb.local_settings import DEBUG
from microweb.local_settings import TEMPLATE_DEBUG
