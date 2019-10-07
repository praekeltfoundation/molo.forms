from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from django.test.client import Client

from molo.core.models import SiteLanguageRelation, Main, Languages
from molo.core.tests.base import MoloTestCaseMixin
from molo.forms.models import (MoloFormPage, MoloFormField,
                               FormsIndexPage, FormTermsConditions,
                               FormsTermsAndConditionsIndexPage)

User = get_user_model()


class TestFormViews(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.client = Client()
        self.mk_main()
        self.main = Main.objects.all().first()
        self.language_setting = Languages.objects.create(
            site_id=self.main.get_site().pk)
        self.english = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting,
            locale='en',
            is_active=True)

        # Create forms index pages
        self.forms_index = FormsIndexPage.objects.child_of(
            self.main).first()

        # create terms and conditions index_page
        terms_conditions_index = FormsTermsAndConditionsIndexPage(
            title='terms and conditions pages', slug='terms-1')
        self.forms_index.add_child(instance=terms_conditions_index)
        terms_conditions_index.save_revision().publish()

        # create terms and conditions page
        self.article = self.mk_article(
            terms_conditions_index, title='ts and cs')

        self.user = User.objects.create_user(
            username='tester',
            email='tester@example.com',
            password='tester')

        self.mk_main2()
        self.main2 = Main.objects.all().last()
        self.language_setting2 = Languages.objects.create(
            site_id=self.main2.get_site().pk)
        self.english2 = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting2,
            locale='en',
            is_active=True)
        self.mk_main2(title='main3', slug='main3', path="00010003")
        self.client2 = Client(HTTP_HOST=self.main2.get_site().hostname)

    def create_molo_form_page(self, parent, **kwargs):
        molo_form_page = MoloFormPage(
            title='Test Form', slug='test-form',
            introduction='Introduction to Test Form ...',
            thank_you_text='Thank you for taking the Test Form',
            submit_text='form submission text',
            **kwargs
        )

        parent.add_child(instance=molo_form_page)
        molo_form_page.save_revision().publish()
        molo_form_field = MoloFormField.objects.create(
            page=molo_form_page,
            sort_order=1,
            label='Your favourite animal',
            field_type='singleline',
            required=True
        )
        return molo_form_page, molo_form_field

    def test_copying_main_copies_forms_relations_correctly(self):
        self.user = self.login()
        # create form page
        molo_form_page, molo_form_field = \
            self.create_molo_form_page(
                parent=self.forms_index,
                homepage_button_text='share your story yo')

        # create the terms and conditions relation with form page
        FormTermsConditions.objects.create(
            page=molo_form_page, terms_and_conditions=self.article)
        # copy one main to create another
        response = self.client.post(reverse(
            'wagtailadmin_pages:copy',
            args=(self.main.id,)),
            data={
                'new_title': 'blank',
                'new_slug': 'blank',
                'new_parent_page': self.root.id,
                'copy_subpages': 'true',
                'publish_copies': 'true'})
        self.assertEqual(response.status_code, 302)
        main3 = Main.objects.get(slug='blank')
        self.assertEqual(
            main3.get_children().count(), self.main.get_children().count())

        # it should replace the terms and conditions page with the new one
        relation = MoloFormPage.objects.descendant_of(
            main3).first().terms_and_conditions.first()
        self.assertTrue(relation.terms_and_conditions.is_descendant_of(main3))
