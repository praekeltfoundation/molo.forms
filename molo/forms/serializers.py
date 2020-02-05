from collections import OrderedDict

from rest_framework import serializers

from wagtail.api.v2.serializers import PageSerializer
from .models import MoloFormPage


class FormFieldSerializer(serializers.Field):
    """
    Serializes the "form_fields" field.

    Example:
    "children": {
        "count": 1,
        "listing_url": "/api/v1/pages/?child_of=2"
    }
    """
    def get_attribute(self, instance):
        return instance

    def to_representation(self, form):
        # get_data_fields
        if form.form_fields.all():
            items = []
            for item in form.form_fields.all():
                items.append({
                    "id": item.id, "sort_order": item.sort_order,
                    "label": item.label, "required": item.required,
                    "default_value": item.default_value,
                    "help_text": item.help_text, "page_break": item.page_break,
                    "admin_label": item.admin_label, "choices": item.choices,
                    "field_type": item.field_type,
                    "input_name": item.clean_name})
            return OrderedDict([
                ("items", items),
            ])


class MoloFormSerializer(PageSerializer):
    class Meta:
        model = MoloFormPage

    form_fields = FormFieldSerializer(read_only=True)
