# Adding Molo Forms to a Djagno project

Molo forms is currently compatible with Django 3.0, 3.1 First, install the molo forms package from PyPI:
```
$ pip install molo.forms
```

## Settings

In your settings add the following to `INSTALLED_APPS`:

```
'molo',
'molo.profiles',
'molo.forms',
```

Add the following entry to `MIDDLEWARE`:

```
'molo.core.middleware.ForceDefaultLanguageMiddleware',
'molo.core.middleware.SetLangaugeCodeMiddleware',
'molo.core.middleware.SetSiteMiddleware',
'molo.core.middleware.MultiSiteRedirectToHomepage',
```

## URL configuration
Now make the following additions to your `urls.py` file:

```
from django.urls import re_path, include


urlpatterns = [
    ...
    re_path(r'^forms/', include(('molo.forms.urls', 'molo.forms'),)),
    ...
]
```

## Start developing
