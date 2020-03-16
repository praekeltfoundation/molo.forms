from molo.core.utils import generate_slug
from molo.core.tests.base import MoloTestCaseMixin

from molo.forms.models import (
    MoloFormPage,
    MoloFormField,
    FormsIndexPage,
    ReactionQuestion,
    PersonalisableForm,
    ReactionQuestionChoice,
    PersonalisableFormField,
    ReactionQuestionIndexPage,
    ArticlePageReactionQuestions
)
from .utils import skip_logic_data


class FormsTestCase(MoloTestCaseMixin):
    def get_reaction_index(self, parent):
        index_page = ReactionQuestionIndexPage.objects.child_of(parent)
        return index_page.first()

    def mk_reaction_question(self, parent, article, **kwargs):
        data = {}
        data.update({
            'title': 'Test Question',
        })
        data.update(kwargs)
        data.update({
            'slug': generate_slug(data['title'])
        })
        question = ReactionQuestion(**data)
        parent.add_child(instance=question)
        question.save_revision().publish()
        choice1 = ReactionQuestionChoice(
            title='yes', success_message='well done')
        question.add_child(instance=choice1)
        choice1.save_revision().publish()
        choice2 = ReactionQuestionChoice(title='maybe')
        question.add_child(instance=choice2)
        choice2.save_revision().publish()
        choice3 = ReactionQuestionChoice(title='no')
        question.add_child(instance=choice3)
        choice3.save_revision().publish()
        ArticlePageReactionQuestions.objects.create(
            reaction_question=question, page=article)
        return question

    def mk_reaction_translation(self, source, article, language, **kwargs):
        instance = self.mk_reaction_question(
            source.get_parent(), article, **kwargs)
        return self.mk_translation(source, language, instance)


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
