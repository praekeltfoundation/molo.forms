from molo.forms.models import (
    MoloFormField,
    MoloFormPage,
    PersonalisableForm,
    FormsIndexPage,
    PersonalisableFormField
)
from .utils import skip_logic_data


class MoloFormsTestMixin:

    def create_molo_form_page_with_field(
        self, parent, display_form_directly=False,
        allow_anonymous_submissions=False, **kwargs
    ):
        molo_form_page = create_molo_form_page(
            parent,
            display_form_directly=display_form_directly,
            allow_anonymous_submissions=allow_anonymous_submissions, **kwargs)
        molo_form_page.save_revision().publish()
        molo_form_field = create_molo_form_formfield(
            form=molo_form_page,
            field_type='singleline',
            label="Your favourite animal",
            required=True)
        return (molo_form_page, molo_form_field)


def create_molo_form_field(form, sort_order, obj):
    if obj['type'] == 'radio':
        skip_logic = skip_logic_data(choices=obj['choices'])
    else:
        skip_logic = None

    return MoloFormField.objects.create(
        page=form,
        sort_order=sort_order,
        label=obj["question"],
        field_type=obj["type"],
        required=obj["required"],
        page_break=obj["page_break"],
        admin_label=obj["question"].lower().replace(" ", "_"),
        skip_logic=skip_logic
    )


def create_molo_form_page(
        parent, title="Test Form", slug='test-form',
        thank_you_text='Thank you for taking the Test Form',
        homepage_introduction='Shorter homepage introduction',
        **kwargs):
    molo_form_page = MoloFormPage(
        title=title, slug=slug,
        introduction='Introduction to Test Form ...',
        thank_you_text=thank_you_text,
        submit_text='form submission text',
        homepage_introduction=homepage_introduction, **kwargs
    )

    parent.add_child(instance=molo_form_page)
    molo_form_page.save_revision().publish()

    return molo_form_page


def create_personalisable_form_page(
        parent, title="Test Personalisable Form",
        slug='test-personalisable-form',
        thank_you_text='Thank you for taking the Personalisable Form',
        **kwargs):
    personalisable_form_page = PersonalisableForm(
        title=title, slug=slug,
        introduction='Introduction to Test Personalisable Form ...',
        thank_you_text=thank_you_text,
        submit_text='personalisable form submission text',
        **kwargs
    )

    parent.add_child(instance=personalisable_form_page)
    personalisable_form_page.save_revision().publish()

    return personalisable_form_page


def create_form(fields={}, **kwargs):
    form = create_molo_form_page(FormsIndexPage.objects.first())

    if not fields == {}:
        num_questions = len(fields)
        for index, field in enumerate(reversed(fields)):
            sort_order = num_questions - (index + 1)
            create_molo_form_field(form, sort_order, field)
    return form


def create_molo_dropddown_field(
        parent, form, choices, page_break=False,
        sort_order=1, label="Is this a dropdown?", **kwargs):
    return MoloFormField.objects.create(
        page=form,
        sort_order=sort_order,
        admin_label="is-this-a-drop-down",
        label=label,
        field_type='dropdown',
        skip_logic=skip_logic_data(choices),
        required=True,
        page_break=page_break
    )


def create_personalisable_dropddown_field(
        parent, form, choices, page_break=False,
        sort_order=1, label="Is this a dropdown?", **kwargs):
    return PersonalisableFormField.objects.create(
        page=form,
        sort_order=sort_order,
        admin_label="is-this-a-drop-down",
        label=label,
        field_type='dropdown',
        skip_logic=skip_logic_data(choices),
        required=True,
        page_break=page_break
    )


def create_molo_form_formfield(
        form, field_type, label="Your favourite animal",
        required=False, sort_order=1):
    return MoloFormField.objects.create(
        page=form,
        sort_order=sort_order,
        label=label,
        field_type=field_type,
        required=required
    )
