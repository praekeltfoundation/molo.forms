from django.urls import re_path

from molo.forms.views import index

urlpatterns = [
    # re-route to overwritten index view, originally in wagtailforms
    re_path(r'^$', index, name='index'),
]
