from wagtail.contrib.modeladmin.options import ModelAdmin

from .models import FormsSegmentUserGroup


class SegmentUserGroupAdmin(ModelAdmin):
    model = FormsSegmentUserGroup
    menu_label = 'User groups for segments'
    menu_icon = 'group'
    menu_order = 1
    add_to_settings_menu = True
    list_display = ('name',)
    search_fields = ('name',)
