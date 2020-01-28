
molo.forms
=============================

.. image:: https://img.shields.io/travis/praekeltfoundation/molo.forms.svg
        :target: https://travis-ci.org/praekeltfoundation/molo.forms

.. image:: https://img.shields.io/pypi/v/molo.forms.svg
        :target: https://pypi.python.org/pypi/molo.forms

.. image:: https://coveralls.io/repos/praekeltfoundation/molo.forms/badge.png?branch=develop
    :target: https://coveralls.io/r/praekeltfoundation/molo.forms?branch=develop
    :alt: Code Coverage

A form builder for Molo applications

Installation::

   pip install molo.forms

Testing:
   read the .travis.yml file
   follow the instructions under the scripts heading

Django setup::

   INSTALLED_APPS = (
      # ...
      'molo.forms',
      # ...

   )


In your urls.py::

    from molo.forms import urls
     ...
     url(r"^forms/$", include(urls)),
     ...


In your main.html::

   {% load molo_forms_tags %}

   {% block content %}
      {% forms_list %}
   {% endblock %}


In your section page or article page::

   {% load molo_forms_tags %}

   {% block content %}
    {{% forms_list_for_pages page=self %}
   {% endblock %}

