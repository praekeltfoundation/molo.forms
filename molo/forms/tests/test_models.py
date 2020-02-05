from django.core.exceptions import ValidationError
from django.test import TestCase
from molo.core.tests.base import MoloTestCaseMixin
from molo.core.models import (
    Main, SiteLanguageRelation, Languages
)
from molo.forms.blocks import SkipLogicBlock, SkipState
from molo.forms.models import (
    MoloFormField,
    MoloFormPage,
    MoloFormSubmission,
    FormsIndexPage,
    PersonalisableForm,
    PersonalisableFormField
)

from .utils import skip_logic_block_data, skip_logic_data
from .base import create_form


class TestFormModels(TestCase, MoloTestCaseMixin):
    def test_submission_class(self):
        submission_class = MoloFormPage().get_submission_class()

        self.assertIs(submission_class, MoloFormSubmission)

    def test_submission_class_get_data_includes_username(self):
        data = MoloFormPage().get_submission_class()(
            form_data='{}'
        ).get_data()
        self.assertIn('username', data)

    def test_submission_class_get_data_converts_list_to_string(self):
        data = MoloFormPage().get_submission_class()(
            form_data='{"checkbox-question": ["option 1", "option 2"]}'
        ).get_data()
        self.assertIn('checkbox-question', data)
        self.assertEqual(data['checkbox-question'], u"option 1, option 2")

    def test_model_validation(self):
        data = {
            'path': '001',
            'depth': '1',
            'title': 'title',
            'slug': 'title',
        }
        with self.assertRaises(ValidationError) as e:
            expected_error = '"Display Question Directly" and "Multi-step" ' \
                             'can not be both selected at the same time'
            MoloFormPage.objects.create(
                multi_step=True, display_form_directly=True,
                **data
            )
            self.assertEqual(e, expected_error)

    def test_your_words_competition_flag(self):
        with self.assertRaises(ValidationError) as e:
            error = '"{}" and "{}" can not be both selected at the same time'\
                .format('Is YourWords Competition', 'Is contact form')

            MoloFormPage.objects.create(
                # parent=self.forms_index,
                title="yourwords form title",
                slug="yourwords_form_title",
                contact_form=True,
                your_words_competition=True,
            )
            self.assertEqual(e, error)


class TestSkipLogicMixin(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.mk_main()
        self.field_choices = ['old', 'this', 'is']
        self.form = MoloFormPage(
            title='Test Form',
            slug='test-form',
        )
        self.section_index.add_child(instance=self.form)
        self.form.save_revision().publish()
        self.choice_field = MoloFormField.objects.create(
            page=self.form,
            sort_order=1,
            label='Your favourite animal',
            field_type='dropdown',
            skip_logic=skip_logic_data(self.field_choices),
            required=True
        )
        self.normal_field = MoloFormField.objects.create(
            page=self.form,
            sort_order=2,
            label='Your other favourite animal',
            field_type='singleline',
            required=True
        )
        self.positive_number_field = MoloFormField.objects.create(
            page=self.form,
            sort_order=3,
            label='How old are you',
            field_type='positive_number',
            required=True
        )

    def test_form_options_512_limit_overriden(self):
        field_choices = [
            'My favourite animal is a dog, because they bark',
            'My favourite animal is a cat, because they meuow',
            'My favourite animal is a bird, because they fly',
            'My favourite animal is a lion, because that roar',
            'My favourite animal is a hamster, because they have tiny legs',
            'My favourite animal is a tiger, because they have stripes',
            'My favourite animal is a frog, because they go crickit',
            'My favourite animal is a fish, because they have nice eyes',
            'My favourite animal is a chicken, because they cannot fly',
            'My favourite animal is a duck, because they keep it down',
            'My favourite animal is a wolf, because they howl',
            'My favourite animal is a chamelion, because they fit in',
        ]
        choice_field = MoloFormField.objects.create(
            page=self.form,
            sort_order=1,
            label='Your favourite animal',
            field_type='dropdown',
            skip_logic=skip_logic_data(field_choices),
            required=True
        )
        self.assertTrue(len(choice_field.choices) > 512)

    def test_choices_updated_from_streamfield_on_save(self):
        self.assertEqual(
            ','.join(self.field_choices),
            self.choice_field.choices
        )

        new_choices = ['this', 'is', 'new']
        self.choice_field.skip_logic = skip_logic_data(new_choices)
        self.choice_field.save()

        self.assertEqual(','.join(new_choices), self.choice_field.choices)

    def test_normal_field_is_not_skippable(self):
        self.assertFalse(self.normal_field.has_skipping)

    def test_positive_number_field_is_not_skippable(self):
        self.assertFalse(self.positive_number_field.has_skipping)

    def test_only_next_doesnt_skip(self):
        self.assertFalse(self.choice_field.has_skipping)

    def test_other_logic_does_skip(self):
        self.choice_field.skip_logic = skip_logic_data(['choice'], ['end'])
        self.choice_field.save()
        self.assertTrue(self.choice_field.has_skipping)


class TestSkipLogicBlock(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.mk_main()
        self.form = MoloFormPage(
            title='Test Form',
            slug='test-form',
        )
        self.section_index.add_child(instance=self.form)
        self.form.save_revision().publish()

    def test_form_raises_error_if_no_object(self):
        block = SkipLogicBlock()
        data = skip_logic_block_data(
            'next form',
            SkipState.FORM,
            form=None,
        )
        with self.assertRaises(ValidationError):
            block.clean(data)

    def test_form_passes_with_object(self):
        block = SkipLogicBlock()
        data = skip_logic_block_data(
            'next form',
            SkipState.FORM,
            form=self.form.id,
        )
        cleaned_data = block.clean(data)
        self.assertEqual(cleaned_data['skip_logic'], SkipState.FORM)
        self.assertEqual(cleaned_data['form'], self.form)

    def test_question_raises_error_if_no_object(self):
        block = SkipLogicBlock()
        data = skip_logic_block_data(
            'a question',
            SkipState.QUESTION,
            question=None,
        )
        with self.assertRaises(ValidationError):
            block.clean(data)

    def test_question_passes_with_object(self):
        block = SkipLogicBlock()
        data = skip_logic_block_data(
            'a question',
            SkipState.QUESTION,
            question=1,
        )
        cleaned_data = block.clean(data)
        self.assertEqual(cleaned_data['skip_logic'], SkipState.QUESTION)
        self.assertEqual(cleaned_data['question'], 1)


class TestPageBreakWithTwoQuestionsInOneStep(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.mk_main()
        self.main = Main.objects.all().first()
        self.language_setting = Languages.objects.create(
            site_id=self.main.get_site().pk)
        self.english = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting,
            locale='en',
            is_active=True)
        self.login()

    def test_setup(self):
        self.assertEqual(1, FormsIndexPage.objects.count())

        create_form()

        self.assertEqual(1, MoloFormPage.objects.count())

    def test_setup2(self):
        create_form([{
            "question":
                "Why do you feel that way about speaking your opinion?",
            "type": 'multiline',
            "required": False,
            "page_break": True,
        }, ])

        self.assertEqual(1, MoloFormPage.objects.count())

    def test_two_questions_in_one_step_when_one_required(self):
        create_form([
            {
                "question": "I feel I can be myself around other people",
                "type": 'radio',
                "choices": ["agree", "disagree"],
                "required": True,
                "page_break": True,
            },
            {
                "question": "I can speak my opinion",
                "type": 'radio',
                "choices": ["yes", "no", "maybe"],
                "required": True,
                "page_break": False,
            },
            {
                "question":
                    "Why do you feel that way about speaking your opinion?",
                "type": 'multiline',
                "required": False,
                "page_break": True,
            },
            {
                "question":
                    "I am able to stand up for myself and what I believe in",
                "type": 'radio',
                "choices": ["Strongly disagree", "I don't know"],
                "required": True,
                "page_break": False,
            },
        ],
            language=self.english)

        self.assertEqual(1, MoloFormPage.objects.count())

        form = MoloFormPage.objects.last()

        self.assertEqual(4, form.form_fields.count())

        field_1 = form.form_fields.all()[0]

        self.assertEqual(
            field_1.skip_logic.stream_data[0]['value']['choice'],
            "agree"
        )
        self.assertEqual(
            field_1.skip_logic.stream_data[0]['value']['skip_logic'],
            "next"
        )
        self.assertEqual(field_1.sort_order, 0)

        field_2 = form.form_fields.all()[1]

        self.assertEqual(
            field_2.skip_logic.stream_data[0]['value']['choice'],
            "yes"
        )
        self.assertEqual(
            field_2.skip_logic.stream_data[0]['value']['skip_logic'],
            "next"
        )
        self.assertEqual(field_2.sort_order, 1)

        field_3 = form.form_fields.all()[2]
        self.assertEqual(field_3.sort_order, 2)

        field_4 = form.form_fields.all()[3]

        self.assertEqual(
            field_4.skip_logic.stream_data[0]['value']['choice'],
            "Strongly disagree"
        )
        self.assertEqual(
            field_4.skip_logic.stream_data[0]['value']['skip_logic'],
            "next"
        )
        self.assertEqual(field_4.sort_order, 3)

        response = self.client.get(form.url)

        self.assertContains(response, field_1.label)
        self.assertContains(response, 'Next Question')
        self.assertContains(response, 'action="' + form.url + '?p=2"')

        response = self.client.post(form.url + '?p=2', {
            field_1.clean_name:
                field_1.skip_logic.stream_data[0]['value']['choice'],
        })
        self.assertContains(response, field_2.label)
        self.assertContains(response, field_3.label)

        response = self.client.post(form.url + '?p=3', {
            field_3.clean_name: 'because ;)',
        }, follow=True)

        self.assertContains(response, "This field is required")
        self.assertContains(response, 'action="' + form.url + '?p=3"')

        response = self.client.post(form.url + '?p=3', {
            field_2.clean_name:
                field_2.skip_logic.stream_data[0]['value']['choice'],
            field_3.clean_name: 'because ;)',
        })

        self.assertContains(response, field_4.label)

        response = self.client.post(form.url + '?p=4', follow=True)
        self.assertContains(response, "This field is required")

        response = self.client.post(form.url + '?p=4', {
            field_4.clean_name:
                field_4.skip_logic.stream_data[0]['value']['choice'],
        }, follow=True)

        self.assertContains(response, form.thank_you_text)

    def test_two_questions_in_last_step_when_one_required(self):
        create_form([
            {
                "question": "I feel I can be myself around other people",
                "type": 'radio',
                "choices": ["agree", "disagree"],
                "required": True,
                "page_break": True,
            },
            {
                "question": "I can speak my opinion",
                "type": 'radio',
                "choices": ["yes", "no", "maybe"],
                "required": True,
                "page_break": False,
            },
            {
                "question":
                    "Why do you feel that way about speaking your opinion?",
                "type": 'multiline',
                "required": False,
                "page_break": False,
            },
        ])

        self.assertEqual(1, MoloFormPage.objects.count())

        form = MoloFormPage.objects.last()

        self.assertEqual(3, form.form_fields.count())

        field_1 = form.form_fields.all()[0]

        self.assertEqual(
            field_1.skip_logic.stream_data[0]['value']['choice'],
            "agree"
        )
        self.assertEqual(
            field_1.skip_logic.stream_data[0]['value']['skip_logic'],
            "next"
        )
        self.assertEqual(field_1.sort_order, 0)

        field_2 = form.form_fields.all()[1]

        self.assertEqual(
            field_2.skip_logic.stream_data[0]['value']['choice'],
            "yes"
        )
        self.assertEqual(
            field_2.skip_logic.stream_data[0]['value']['skip_logic'],
            "next"
        )
        self.assertEqual(field_2.sort_order, 1)

        field_3 = form.form_fields.all()[2]
        self.assertEqual(field_3.sort_order, 2)

        response = self.client.get(form.url)

        self.assertContains(response, field_1.label)
        self.assertContains(response, 'Next Question')

        response = self.client.post(form.url + '?p=2', {
            field_1.clean_name:
                field_1.skip_logic.stream_data[0]['value']['choice'],
        })
        self.assertContains(response, field_2.label)
        self.assertContains(response, field_3.label)

        response = self.client.post(form.url + '?p=3', {
            field_3.clean_name: 'because ;)',
        }, follow=True)

        self.assertContains(response, "This field is required")
        response = self.client.post(form.url + '?p=3', {
            field_2.clean_name:
                field_2.skip_logic.stream_data[0]['value']['choice'],
            field_3.clean_name: 'because ;)',
        }, follow=True)
        self.assertContains(response, form.thank_you_text)


class TestFormFieldDefaultDateValidation(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.mk_main()
        self.login()

    def create_molo_form_field(self, field_type):
        form = MoloFormPage(
            title='Test Form',
            introduction='Introduction to Test Form ...',
        )
        FormsIndexPage.objects.first().add_child(instance=form)
        form.save_revision().publish()

        return MoloFormField.objects.create(
            page=form,
            label="When is your birthday",
            field_type=field_type,
            admin_label="birthday",
        )

    def create_personalisable_form_field(self, field_type):
        form = PersonalisableForm(
            title='Test Form',
            introduction='Introduction to Test Form ...',
        )

        FormsIndexPage.objects.first().add_child(instance=form)
        form.save_revision().publish()

        return PersonalisableFormField.objects.create(
            page=form,
            label="When is your birthday",
            field_type=field_type,
            admin_label="birthday",
        )

    def test_date_molo_form_fields_clean_if_blank(self):
        field = self.create_molo_form_field('date')
        field.default_value = ""
        try:
            field.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError with valid content!")

    def test_date_molo_form_fields_clean_with_valid_default(self):
        field = self.create_molo_form_field('date')
        field.default_value = "2008-05-05"
        try:
            field.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError with valid content!")

    def test_date_molo_form_fields_not_clean_with_invalid_default(self):
        field = self.create_molo_form_field('date')
        field.default_value = "something that isn't a date"
        with self.assertRaises(ValidationError) as e:
            field.clean()

        self.assertEqual(e.exception.messages, ['Must be a valid date'])

    def test_datetime_molo_form_fields_clean_if_blank(self):
        field = self.create_molo_form_field('datetime')
        field.default_value = ""
        try:
            field.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError with valid content!")

    def test_datetime_molo_form_fields_clean_with_valid_default(self):
        field = self.create_molo_form_field('datetime')
        field.default_value = "2008-05-05"
        try:
            field.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError with valid content!")

    def test_datetime_molo_form_fields_not_clean_with_invalid_default(self):
        field = self.create_molo_form_field('datetime')
        field.default_value = "something that isn't a date"
        with self.assertRaises(ValidationError) as e:
            field.clean()

        self.assertEqual(e.exception.messages, ['Must be a valid date'])

    def test_date_personalisabe_form_fields_clean_if_blank(self):
        field = self.create_personalisable_form_field('date')
        field.default_value = ""
        try:
            field.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError with valid content!")

    def test_date_personalisabe_form_fields_clean_with_valid_default(self):
        field = self.create_personalisable_form_field('date')
        field.default_value = "2008-05-05"
        try:
            field.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError with valid content!")

    def test_date_personalisable_fields_not_clean_with_invalid_default(self):
        field = self.create_personalisable_form_field('date')
        field.default_value = "something that isn't a date"
        with self.assertRaises(ValidationError) as e:
            field.clean()

        self.assertEqual(e.exception.messages, ['Must be a valid date'])

    def test_datetime_personalisabe_form_fields_clean_if_blank(self):
        field = self.create_personalisable_form_field('datetime')
        field.default_value = ""
        try:
            field.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError with valid content!")

    def test_datetime_personalisabe_form_fields_clean_with_valid_default(self):
        field = self.create_personalisable_form_field('datetime')
        field.default_value = "2008-05-05"
        try:
            field.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError with valid content!")

    def test_datetime_personalisable_fields_not_clean_with_invalid_default(
            self):
        field = self.create_personalisable_form_field('datetime')
        field.default_value = "something that isn't a date"
        with self.assertRaises(ValidationError) as e:
            field.clean()

        self.assertEqual(e.exception.messages, ['Must be a valid date'])
