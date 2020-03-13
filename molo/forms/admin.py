from django.urls import reverse
from django.contrib import admin
from wagtail.contrib.modeladmin.options import (
    ModelAdmin as WagtailModelAdmin,
    modeladmin_register, ModelAdminGroup,
)

from molo.core.models import ArticlePage
from .models import (
    FormsSegmentUserGroup, ReactionQuestion,
    ReactionQuestionResponse,
)


class SegmentUserGroupAdmin(WagtailModelAdmin):
    model = FormsSegmentUserGroup
    menu_label = 'User groups for segments'
    menu_icon = 'group'
    menu_order = 1
    add_to_settings_menu = True
    list_display = ('name',)
    search_fields = ('name',)


class ReactionQuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'live')
    fieldsets = (
        (
            None,
            {'fields': ('title', )}
        ),
    )
    readonly_fields = ['title']


class ReactionQuestionResponseAdmin(WagtailModelAdmin):
    model = ReactionQuestionResponse
    list_display = ('question', 'choice', 'user', 'article')
    fieldsets = (
        (
            None,
            {'fields': ('question', 'choice', 'user', 'article')}
        ),
    )
    readonly_fields = ['question', 'choice']


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


class ArticlePageProxy(ArticlePage):
    class Meta:
        proxy = True
        verbose_name = 'Article Page'


class ReactionQuestionsSummaryModelAdmin(
        WagtailModelAdmin, ReactionQuestionAdmin):
    model = ArticlePageProxy
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


modeladmin_register(SegmentUserGroupAdmin)
modeladmin_register(ReactionQuestionsGroup)
modeladmin_register(ReactionQuestionsModelAdmin)
modeladmin_register(ReactionQuestionsSummaryModelAdmin)
