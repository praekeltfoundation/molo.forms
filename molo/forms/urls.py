
from django.conf.urls import url
from molo.forms.views import (
    FormSuccess, ResultsPercentagesJson, submission_article,
    get_segment_user_count
)


urlpatterns = [
    url(
        r"^(?P<slug>[\w-]+)/success/$",
        FormSuccess.as_view(),
        name="success"
    ),
    url(
        r"^(?P<slug>[\w-]+)/results_json/$",
        ResultsPercentagesJson.as_view(),
        name="results_json"
    ),
    url(
        r'^submissions/(\d+)/article/(\d+)/$',
        submission_article, name='article'
    ),
    url(
        r"^count/$",
        get_segment_user_count,
        name="segmentusercount"
    ),
]
