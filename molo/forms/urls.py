
from django.urls import re_path
from molo.forms.views import (
    FormSuccess, ResultsPercentagesJson, submission_article,
    get_segment_user_count
)


urlpatterns = [
    re_path(
        r"^(?P<slug>[\w-]+)/success/$",
        FormSuccess.as_view(),
        name="success"
    ),
    re_path(
        r"^(?P<slug>[\w-]+)/results_json/$",
        ResultsPercentagesJson.as_view(),
        name="results_json"
    ),
    re_path(
        r'^submissions/(\d+)/article/(\d+)/$',
        submission_article, name='article'
    ),
    re_path(
        r"^count/$",
        get_segment_user_count,
        name="segmentusercount"
    ),
]
