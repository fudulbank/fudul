"""
Django settings for fudul project.

Generated by 'django-admin startproject' using Django 1.11.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import random
from . import secrets
from django.urls import reverse_lazy

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = secrets.SECRET_KEY

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = getattr(secrets, 'DEBUG', False)

ALLOWED_HOSTS = ['.fudulbank.com', '127.0.0.1','127.0.0.1:8000']


# Application definition

INSTALLED_APPS = [
    'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.humanize',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'haystack',
    'silk',
    'rest_framework',
    'django_js_reverse',
    'rules',
    'mailer',
    'htmlmin',
    'loginas',
    'bootstrap4',
    'bootstrap3',
    'post_office',
    'core',
    'notifications',
    'accounts',
    'userena',
    'guardian',
    'easy_thumbnails',
    'exams',
    'teams',
    'ckeditor',
    'ckeditor_uploader',
    'constance',
    'constance.backends.database',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'silk.middleware.SilkyMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fudul.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.universal_context',
                'constance.context_processors.config',
            ],
        },
    },
]

WSGI_APPLICATION = 'fudul.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DEFAULT_DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'new.sqlite3'),
        }
    }
DATABASES = getattr(secrets, 'DATABASES', DEFAULT_DATABASES)

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

if DEBUG:
    AUTH_PASSWORD_VALIDATORS = []

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Riyadh'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = getattr(secrets, 'STATIC_URL', '/static/')
DEFAULT_STATIC_ROOT = os.path.join(BASE_DIR, 'static_files/')
STATIC_ROOT = getattr(secrets, 'STATIC_ROOT', DEFAULT_STATIC_ROOT)
MEDIA_URL = getattr(secrets, 'MEDIA_URL', '/media/')
DEFAULT_MEDIA_ROOT = os.path.join(BASE_DIR, 'media_files/')
MEDIA_ROOT = getattr(secrets, 'MEDIA_ROOT', DEFAULT_MEDIA_ROOT)
CKEDITOR_UPLOAD_PATH = "uploads/"

# Email settings
EMAIL_USE_TLS = getattr(secrets, 'EMAIL_USE_TLS', None)
EMAIL_HOST = getattr(secrets, 'EMAIL_HOST', None)
EMAIL_PORT = getattr(secrets, 'EMAIL_PORT', None)
EMAIL_HOST_USER = getattr(secrets, 'EMAIL_HOST_USER', None)
EMAIL_HOST_PASSWORD = getattr(secrets, 'EMAIL_HOST_PASSWORD', None)
EMAIL_BACKEND = getattr(secrets, "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_FILE_PATH = 'core/email-messages/'
DEFAULT_FROM_EMAIL = 'noreply@fudulbank.com'
SERVER_EMAIL = 'errors@fudulbank.com'
ADMINS = [('Errors', 'errors@fudulbank.com')]


# External API keys
SOCIAL_AUTH_TWITTER_KEY = getattr(secrets, "SOCIAL_AUTH_TWITTER_KEY", "")
SOCIAL_AUTH_TWITTER_SECRET = getattr(secrets, "SOCIAL_AUTH_TWITTER_SECRET", "")

# Session
SESSION_ENGINE = getattr(secrets, "SESSION_ENGINE", "django.contrib.sessions.backends.db")

# Security settings
SESSION_COOKIE_DOMAIN = getattr(secrets, "SESSION_COOKIE_DOMAIN", None)
CSRF_COOKIE_DOMAIN = getattr(secrets, "CSRF_COOKIE_DOMAIN", None)
SECURE_HSTS_SECONDS = getattr(secrets, "SECURE_HSTS_SECONDS", None)


# Userena settings
AUTHENTICATION_BACKENDS = (
    'fudul.backends.UserAuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
    'rules.permissions.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
)
SITE_ID = 1
ANONYMOUS_USER_NAME = 'AnonymousUser'
AUTH_PROFILE_MODULE = 'accounts.Profile'
LOGIN_URL = reverse_lazy('userena_signin')
LOGOUT_URL = reverse_lazy('loginas-logout')
LOGINAS_LOGOUT_REDIRECT_URL = reverse_lazy('index')
LOGIN_REDIRECT_URL = USERENA_SIGNIN_REDIRECT_URL = reverse_lazy('index')
LOGOUT_REDIRECT_URL = USERENA_REDIRECT_ON_SIGNOUT = reverse_lazy('index')
USERENA_WITHOUT_USERNAMES = True
USERENA_ACTIVATION_RETRY = True
USERENA_ACTIVATION_DAYS = 30

CKEDITOR_CONFIGS = {
    'default': {
        'skin': 'moono-lisa',
        # 'skin': 'office2013',
        'toolbar_Basic': [
            ['Source', '-', 'Bold', 'Italic']
        ],
        'toolbar_YourCustomToolbarConfig': [
            {'name': 'document', 'items': ['Source', '-', 'Save', 'NewPage', 'Preview', 'Print', '-', 'Templates']},
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': ['Find', 'Replace', '-', 'SelectAll']},
            {'name': 'forms',
             'items': ['Form', 'Checkbox', 'Radio', 'TextField', 'Textarea', 'Select', 'Button', 'ImageButton',
                       'HiddenField']},
            '/',
            {'name': 'basicstyles',
             'items': ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', 'RemoveFormat']},
            {'name': 'paragraph',
             'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote', 'CreateDiv', '-',
                       'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock', '-', 'BidiLtr', 'BidiRtl',
                       'Language']},
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'insert',
             'items': ['Image', 'Flash', 'Table', 'HorizontalRule', 'Smiley', 'SpecialChar', 'PageBreak', 'Iframe']},
            '/',
            {'name': 'styles', 'items': ['Styles', 'Format', 'Font', 'FontSize']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'tools', 'items': ['Maximize', 'ShowBlocks']},
            {'name': 'about', 'items': ['About']},
            '/',  # put this to force next toolbar on new line
            {'name': 'yourcustomtools', 'items': [
                # put the name of your editor.ui.addButton here
                'Preview',
                'Maximize',

            ]},
        ],
        'toolbar': 'YourCustomToolbarConfig',  # put selected toolbar config here
        # 'toolbarGroups': [{ 'name': 'document', 'groups': [ 'mode', 'document', 'doctools' ] }],
        # 'height': 291,
        # 'width': '100%',
        # 'filebrowserWindowHeight': 725,
        # 'filebrowserWindowWidth': 940,
        # 'toolbarCanCollapse': True,
        # 'mathJaxLib': '//cdn.mathjax.org/mathjax/2.2-latest/MathJax.js?config=TeX-AMS_HTML',
        'tabSpaces': 4,
        'extraPlugins': ','.join([
            'uploadimage', # the upload image feature
            # your extra plugins here
            'div',
            'autolink',
            'autoembed',
            'embedsemantic',
            'autogrow',
            # 'devtools',
            'widget',
            'lineutils',
            'clipboard',
            'dialog',
            'dialogui',
            'elementspath'
        ]),
    }
}

PRIVILEGED_DIR = os.path.join(BASE_DIR, 'privileged_files/')
DJANGO_NOTIFICATIONS_CONFIG = {'SOFT_DELETE': True,
                               'USE_JSONFIELD': True}

DEFAULT_CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
CACHES = getattr(secrets, 'CACHES', DEFAULT_CACHES)

JS_REVERSE_EXCLUDE_NAMESPACES = ['teams', 'mailer', 'silk', 'notifications']

# To standardize caching time.
CACHE_PERIODS = {'STABLE': 60 * 60 * 24 * 7,  # 7 days
                 'EXPENSIVE_CHANGEABLE': 60 * 60 * 4, # 4 hours
                 'EXPENSIVE_UNCHANGEABLE': 60 * 60 * 12, # 12 hours
                 'DYNAMIC': 60 * 5, # 10 minutes
}


# django-silk settings 
SILKY_AUTHENTICATION = True
SILKY_AUTHORISATION = True
SILKY_PYTHON_PROFILER = True
SILKY_PERMISSIONS = lambda user: user.is_superuser
SILKY_MAX_REQUEST_BODY_SIZE = -1
SILKY_MAX_RESPONSE_BODY_SIZE = 1024
SILKY_MAX_RECORDED_REQUESTS = 1000
SILKY_META = True

# In production, we want to collect random request.
if DEBUG:
    SILKY_INTERCEPT_FUNC = lambda request: 'HTTP_X_SILKY' in request.META
else:
    SILKY_INTERCEPT_FUNC = lambda request: 'HTTP_X_SILKY' in request.META or random.randint(1, 100) == 1

# Constance settings
CONSTANCE_CONFIG = {
    'DONATION_ACTIVATED': (False, 'Donation campaign is activated.'),
    'DONATION_TARGET': (1, 'The total amount we are trying to fundraise'),
    'WF_CURRENT_BALANCE': (0, 'The amount currently in our WebFaction account'),
    'WF_SESSION_ID': ('', 'A valid session id to use to login to WebFaction control panel'),
}
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
CONSTANCE_DATABASE_CACHE_BACKEND = getattr(secrets, "CONSTANCE_DATABASE_CACHE_BACKEND", None)

# Haystack settings
DEFAULT_HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
}
HAYSTACK_CONNECTIONS = getattr(secrets, "HAYSTACK_CONNECTIONS", DEFAULT_HAYSTACK_CONNECTIONS)