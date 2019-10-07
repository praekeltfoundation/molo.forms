from django import template

from wagtail_personalisation.adapters import get_segment_adapter

register = template.Library()


@register.simple_tag
def filter_forms_by_segments(forms, request):
    """Filter out forms not in user's segments."""
    user_segments = get_segment_adapter(request).get_segments()
    user_segments_ids = [s.id for s in user_segments]
    filtered_forms = []

    for form in forms:
        if not hasattr(form['molo_form_page'], 'segment_id') or \
                not form['molo_form_page'].segment_id \
                or form['molo_form_page'].segment_id in user_segments_ids:
            filtered_forms.append(form)

    return filtered_forms
