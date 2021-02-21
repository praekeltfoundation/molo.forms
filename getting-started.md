# Getting started

These instructions assume familiarity with virtual environments and the [Django Web Environment](https://docs.djangoproject.com/en/3.1/)

## Dependencies needed for installation
- Python 3

## Quick install
Run the virtual environment of your choice

```
$ pip install -e .
$ pip install -r requirements-dev.txt
```

(Installing outside a virtual environment may require `sudo`)

Molo core scaffolds each plugin to create a testapp. After installing the requirements run

```
$ molo scaffold testapp --require molo.forms --include molo.forms forms/
```
This will create a testapp folder that will create an instance of the molo forms project that is a django application. Once you see this run the following
```
$ cd testapp
$ ./manage.py migrate
$ ./manage.py createsuperuser
$ ./manage.py runserver
```

Your site is now accessible at `http://localhost:8000`, with the admin backend available at `http://localhost:8000/admin/`.
