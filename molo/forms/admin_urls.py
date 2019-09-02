from django.conf.urls import url

from molo.forms.views import index

urlpatterns = [
    # re-route to overwritten index view, originally in wagtailforms
    url(r'^$', index, name='index'),
]
