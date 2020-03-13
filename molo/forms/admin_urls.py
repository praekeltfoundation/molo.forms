from django.urls import re_path

from molo.forms.views import index
from molo.forms.admin_views import (
    ReactionQuestionResultsAdminView,
    ReactionQuestionSummaryAdminView
)


urlpatterns = [
    # re-route to overwritten index view, originally in wagtailforms
    re_path(r'^$', index, name='index'),
    re_path(
        r'reactionquestion/(?P<parent>\d+)/results/$',
        ReactionQuestionResultsAdminView.as_view(),
        name='reaction-question-results-admin'),

    re_path(
        r'reactionquestion/(?P<article>\d+)/results/summary/$',
        ReactionQuestionSummaryAdminView.as_view(),
        name='reaction-question-article-results-admin'),
]
