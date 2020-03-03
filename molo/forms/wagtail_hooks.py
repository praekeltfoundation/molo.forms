
from django.conf import settings
from django.contrib.admin import ModelAdmin
from django.utils.html import format_html_join
from django.urls import re_path, include, reverse

from wagtail.core import hooks
from wagtail.contrib.modeladmin.options import (
    modeladmin_register, ModelAdminGroup,
    ModelAdmin as WagtailModelAdmin
)

from molo.core.models import ArticlePage
from molo.forms import admin_urls
from molo.forms.admin_views import (
    ReactionQuestionResultsAdminView,
    ReactionQuestionSummaryAdminView
)
from molo.forms.models import (
    MoloFormPage, FormTermsConditions, ReactionQuestion,
)

from .admin import SegmentUserGroupAdmin


modeladmin_register(SegmentUserGroupAdmin)


@hooks.register('insert_global_admin_js')
def global_admin_js():
    js_files = [
        'js/form-admin.js',
    ]

    js_includes = format_html_join(
        '\n', '<script src="{0}{1}"></script>',
        ((settings.STATIC_URL, filename) for filename in js_files)
    )
    return js_includes


@hooks.register('after_copy_page')
def create_new_page_relations(request, page, new_page):
    if page and new_page:
        if new_page.get_descendants().count() >= \
                page.get_descendants().count():
            for form in MoloFormPage.objects.descendant_of(
                    new_page.get_site().root_page):
                # replace old terms and conditions with new one, if it exists
                relations = FormTermsConditions.objects.filter(page=form)
                for relation in relations:
                    if relation.terms_and_conditions:
                        new_article = ArticlePage.objects.descendant_of(
                            new_page.get_site().root_page).filter(
                                slug=relation.terms_and_conditions.slug)\
                            .first()
                        relation.terms_and_conditions = new_article
                        relation.save()


class ReactionQuestionAdmin(ModelAdmin):
    list_display = ('title', 'live')
    fieldsets = (
        (
            None,
            {'fields': ('title', )}
        ),
    )
    readonly_fields = ['title']


class ReactionQuestionsModelAdmin(WagtailModelAdmin, ReactionQuestionAdmin):
    model = ReactionQuestion
    menu_label = 'Reaction Question'
    menu_icon = 'doc-full'
    add_to_settings_menu = False
    list_display = ('responses', 'live')

    def responses(self, obj, *args, **kwargs):
        url = reverse('reaction-question-results-admin', args=(obj.id,))
        return '<a href="%s">%s</a>' % (url, obj)

    def get_queryset(self, request):
        qs = super(ReactionQuestionAdmin, self).get_queryset(request)
        # Only show questions related to that site
        main = request.site.root_page
        return qs.descendant_of(main)

    responses.allow_tags = True
    responses.short_description = 'Title'


class ReactionQuestionsSummaryModelAdmin(
        WagtailModelAdmin, ReactionQuestionAdmin):
    model = ArticlePage
    menu_label = 'Reaction Question Summary'
    menu_icon = 'doc-full'
    add_to_settings_menu = False
    list_display = ('articles', 'live')

    def articles(self, obj, *args, **kwargs):
        url = reverse(
            'reaction-question-article-results-admin', args=(obj.id,))
        return '<a href="%s">%s</a>' % (url, obj)

    def get_queryset(self, request):
        qs = ArticlePage.objects.descendant_of(
            request.site.root_page).filter(
            language__is_main_language=True).exclude(
            reaction_questions=None
        )
        return qs
    articles.allow_tags = True
    articles.short_description = 'Title'


class ReactionQuestionsGroup(ModelAdminGroup):
    menu_label = 'ReactionQuestions'
    menu_icon = 'folder-open-inverse'
    menu_order = 500
    items = (ReactionQuestionsSummaryModelAdmin, ReactionQuestionsModelAdmin)


modeladmin_register(ReactionQuestionsGroup)
modeladmin_register(ReactionQuestionsModelAdmin)
modeladmin_register(ReactionQuestionsSummaryModelAdmin)


@hooks.register('construct_main_menu')
def show_reactionquestions_response_for_users_have_access(request, menu_items):
    excl = [
        'reaction-question',
        'reaction-question-responses',
        'reaction-question-summary',
    ]
    menu_items[:] = [
        item for item in menu_items if item.name not in excl]

    if not request.user.has_perm('forms.can_view_response'):
        menu_items[:] = [
            item for item in menu_items if item.name != 'reactionquestions']

# This overwrites the wagtail surveys admin urls in order to use custom
# form index view
@hooks.register('register_admin_urls')
def register_admin_urls():
    return [
        re_path(r'^forms/', include(admin_urls)),

        re_path(
            r'reactionquestion/(?P<parent>\d+)/results/$',
            ReactionQuestionResultsAdminView.as_view(),
            name='reaction-question-results-admin'),

        re_path(
            r'reactionquestion/(?P<article>\d+)/results/summary/$',
            ReactionQuestionSummaryAdminView.as_view(),
            name='reaction-question-article-results-admin'),
    ]

