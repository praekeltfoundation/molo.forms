# Adding Molo Forms to a Django project

Please follow [these steps](https://docs.wagtail.io/en/stable/getting_started/integrating_into_django.html) to get Wagtail installed into your existing project and [wagtail forms]before adding molo.forms

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

## Adding templates
Molo forms uses Django template library (DTL)

Where you would like to add the list of forms in your html template, add the following:
```
{% load molo_forms_tags %}

{% block content %}
   {% forms_list %}
{% endblock %}
```

Where you would like to an individual form to a Page in your html template add the following:
```
{% load molo_forms_tags %}

{% block content %}
 {{% forms_list_for_pages page=self %}
{% endblock %}
```
Note: page should be the Wagtial Page object. In our example it is set to self.
