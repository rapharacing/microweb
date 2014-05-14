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
    # Redirect to custom domain, if one exists for the site
    'core.middleware.redirect.DomainRedirectMiddleware',

    # Note: if using messages, enable the sessions middleware too
    'django.middleware.common.CommonMiddleware',

    # CSRF protection on form submission
    'django.middleware.csrf.CsrfViewMiddleware',

    # convenience for request context like site, user account, etc.
    'core.middleware.context.ContextMiddleware',

    # cache busting for static files
    'core.middleware.modtimeurls.ModTimeUrlsMiddleware',

    # time all requests and report to riemann
    'core.middleware.timing.TimingMiddleware',

    # push exceptions to riemann
    'core.middleware.exception.ExceptionMiddleware',
    )

ROOT_URLCONF = 'microweb.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'microweb.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'core',
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
    )

CLIENT_ID = 1
CLIENT_SECRET = ''
API_SCHEME = 'https://'
API_DOMAIN_NAME = 'microco.sm'
API_PATH = 'api'
API_VERSION = 'v1'
RIEMANN_ENABLED = False
RIEMANN_HOST = ''
MEMCACHE_HOST = '127.0.0.1'
MEMCACHE_PORT = 11211
PAGE_SIZE = 25
SECRET_KEY = 'changeme'
DEBUG = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        },
    'handlers': {
        'stdout':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        },
    'loggers': {
        'django': {
            'handlers': ['stdout'],
            'level': 'DEBUG',
            'propagate': True,
            },
        'django.request': {
            'handlers': ['stdout'],
            'level': 'DEBUG',
            'propagate': True,
            },
        'microcosm.views': {
            'handlers': ['stdout'],
            'level': 'DEBUG',
            'propagate' : True,
            },
        'microcosm.middleware': {
            'handlers': ['stdout'],
            'level': 'DEBUG',
            'propagate' : True,
            }
    }
}
