from .base import *  # noqa


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django_extensions',
    'django_prometheus',

    'taggit',
    'modelcluster',

    'testapp',
    'molo.core',
    'molo.forms',
    'molo.profiles',
    'mote',
    'google_analytics',

    'wagtail.core',
    'wagtail.admin',
    'wagtail.documents',
    'wagtail.snippets',
    'wagtail.users',
    'wagtail.sites',
    'wagtail.images',
    'wagtail.embeds',
    'wagtail.search',
    'wagtail.contrib.redirects',
    'wagtail.contrib.forms',
    'wagtailmedia',
    'wagtail.contrib.sitemaps',
    'wagtail.contrib.settings',
    'wagtail.contrib.modeladmin',
    'wagtail_personalisation',
    'wagtailfontawesome',
    'wagtail.api.v2',

    'mptt',
    'el_pagination',

    'raven.contrib.django.raven_compat',
    'django_cas_ng',
    'compressor',
]

CELERY_ALWAYS_EAGER = True
BROKER_BACKEND = 'memory'

ALLOWED_HOSTS = [
    'localhost',
    '.localhost',
    'site2',
]

PERSONALISATION_SEGMENTS_ADAPTER = (
    'molo.forms.adapters.PersistentFormsSegmentsAdapter'
)
