# Django settings for sokoban project.

import os

DEBUG = os.environ.get('SOKOBAN_DEBUG', False)
TEMPLATE_DEBUG = DEBUG

ADMINS = (
)

MANAGERS = ADMINS

# You should grant **ONLY** select,delete,alter,create,drop,update,insert
# to user sokoban for two databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'sokoban',
        'USER': 'sokoban',
        'PASSWORD': 'sokoban',
        'HOST': '',
        'PORT': '',
    },
    'sokoban_middle_ware': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'sokoban_middle_ware',
        'USER': 'sokoban',
        'PASSWORD': 'sokoban',
    },
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

USE_TZ = True

TIME_ZONE = 'Asia/Shanghai'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

STATIC_ROOT = '/var/www/sokoban/static/'

STATIC_URL = '/static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

STATICFILES_DIRS = (
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "static"),
)

SECRET_KEY = '@-q_0gxugnuf6$2a!g3b1d^!zwt6w76ruy-!&txw7yl1*d1k+j'

TEMPLATE_LOADERS = (
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.filesystem.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "django.core.context_processors.request",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'sokoban.middleware.TimezoneMiddleware',
)

ROOT_URLCONF = 'sokoban.urls'

WSGI_APPLICATION = 'sokoban.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'sokoban',
    'account',
    'scheduler',
    'suit',
    'django.contrib.admin',
)

AUTH_USER_MODEL = 'account.SimpleUser'
LOGIN_REDIRECT_URL = 'home'

AUTHENTICATION_BACKENDS = (
    'sokoban.backends.auth_backend.ModAuthKerbBackend',
    'sokoban.backends.auth_backend.KerberosBackend',
    'sokoban.backends.auth_backend.SimpleBackend',
)

KRB5_REALM = "REDHAT.COM"

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

SUIT_CONFIG = {
    # header
    'ADMIN_NAME': 'Sokoban Admin',
    # 'HEADER_DATE_FORMAT': 'l, j. F Y',
    # 'HEADER_TIME_FORMAT': 'H:i',

    # forms
    # 'SHOW_REQUIRED_ASTERISK': True,
    # 'CONFIRM_UNSAVED_CHANGES': True,

    # menu
    # 'SEARCH_URL': '/admin/auth/user/',
    # 'MENU_ICONS': {
    #    'sites': 'icon-leaf',
    #    'auth': 'icon-lock',
    # },
    # 'MENU_OPEN_FIRST_CHILD': True, # Default True
    # 'MENU_EXCLUDE': ('auth.group',),
    # 'MENU': (
    #     'sites',
    #     {'app': 'auth', 'icon':'icon-lock', 'models': ('user', 'group')},
    #     {'label': 'Settings', 'icon':'icon-cog', 'models': ('auth.user', 'auth.group')},
    #     {'label': 'Support', 'icon':'icon-question-sign', 'url': '/support/'},
    # ),

    # misc
    # 'LIST_PER_PAGE': 15
}

# I don't want to hard code either. Package system of python sucks!
SOKOBAN_MIDDLE_WARE_ROOT = '/var/lib/sokoban/middle_ware'
SYNCHRONIZATION_LOCK_DIR = '/tmp/sokoban_lock'
SOKOBAN_WORKING_DIRECTORY = '/var/lib/sokoban/working'
SOKOBAN_WORKING_TREE_DIRECTORY = '/var/lib/sokoban/tree'
SOKOBAN_VCS_DIRECTORY = '/var/lib/sokoban/core'
SOKOBAN_SECRET_KEY = 'LLmFjF8ruXKZ8CpMmRB4ksatYhNinwLsdYK2of0tUAo='

VIRTUAL_CONTAINER = 'busyjay/sokoban'

import sys
sys.path.append(SOKOBAN_MIDDLE_WARE_ROOT)

DATETIME_FORMAT = "c"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}
