
from django.urls import re_path
from molo.forms.views import (
    FormSuccess, ResultsPercentagesJson, submission_article,
    get_segment_user_count, MoloFormsEndpoint
)
from molo.core.api.urls import api_router


api_router.register_endpoint("forms", MoloFormsEndpoint)

urlpatterns = [
    re_path(
        r"^(?P<slug>[\w-]+)/success/$",
        FormSuccess.as_view(),
        name="success"
    ),
    re_path(
        r"^(?P<slug>[\w-]+)/(?P<article>[\w-]+)/success/$",
        FormSuccess.as_view(),
        name="success_article_form"
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
