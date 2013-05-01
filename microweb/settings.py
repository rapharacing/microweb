import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Do not change these! Override them in local_settings.py if necessary.
DEBUG = False
TEMPLATE_DEBUG = False

ADMINS = ()
MANAGERS = ADMINS

# Test runner gets unhappy if there's no database defined.
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

USE_I18N = True
USE_L10N = True
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
STATIC_ROOT = '/srv/www/django/microweb/static/'

# URL prefix for static files.
STATIC_URL = '/static/'
STATICFILES_DIRS = ()
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '!ygb2(@l&amp;h1+iy6z6jwiak3e**e3ljb=1fc5#i&amp;1fk#0ve!+!&amp;'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.core.context_processors.static',
)

MIDDLEWARE_CLASSES = (

    # Note: if using messages, enable the sessions middleware too
    'django.middleware.common.CommonMiddleware',
    #'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # convenience for request context like site, user account, etc.
    'microcosm.middleware.context.ContextMiddleware',

    # push exceptions to riemann
    'microcosm.middleware.exception.ExceptionMiddleware',

)

ROOT_URLCONF = 'microweb.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'microweb.wsgi.application'

TEMPLATE_DIRS = ()

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'microcosm',
    'gunicorn',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console':{
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file':{
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'verbose',
            'filename' : os.path.join(PROJECT_ROOT, 'application.log'),
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console','file'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'microcosm.views': {
            'handlers': ['console','file'],
            'level': 'ERROR',
            'propagate' : True,
        },
        'microcosm.middleware': {
            'handlers': ['console','file'],
            'level': 'ERROR',
            'propagate' : True,
            }
    }
}

# Populate the settings below in local_settings.py (see the README for example values).
CLIENT_ID = ''
CLIENT_SECRET = ''
API_ROOT = ''
RIEMANN_ENABLED = False

# Persona test data
PERSONA_USER = ''
PERSONA_PASS = ''
PERSONA_ADMIN = ''
PERSONA_ADMIN_PASS = ''

PAGE_SIZE = 25

# Clobber any settings with those defined in local_settings.py
try:
    from local_settings import *
except ImportError:
    pass
