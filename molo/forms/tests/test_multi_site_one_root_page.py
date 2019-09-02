from django.test import TestCase, Client

from molo.core.models import Main, SiteLanguageRelation, Languages
from molo.core.tests.base import MoloTestCaseMixin
from molo.core.utils import generate_slug
from molo.forms.models import (
    FormsIndexPage,
    MoloFormPage,
    MoloFormField
)
from wagtail.core.models import Site


class TestSites(TestCase, MoloTestCaseMixin):

    def setUp(self):
        self.mk_main()
        self.main = Main.objects.all().first()
        self.english = SiteLanguageRelation.objects.create(
            language_setting=Languages.for_site(self.main.get_site()),
            locale='en',
            is_active=True)
        self.yourmind = self.mk_section(
            self.section_index, title='Your mind')
        self.forms_index = FormsIndexPage.objects.child_of(
            self.main).first()

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

    def test_two_sites_point_to_one_root_page(self):
        # assert that there is only one site rooted at main
        self.assertEqual(self.main.sites_rooted_here.count(), 1)
        client_1 = Client()
        # add a site that points to the same root page
        site_2 = Site.objects.create(
            hostname=generate_slug('site2'), port=80, root_page=self.main)
        # create a link buetween the current langauges and the new site
        Languages.objects.create(
            site_id=site_2.pk)
        SiteLanguageRelation.objects.create(
            language_setting=Languages.for_site(site_2),
            locale='en',
            is_active=True)
        client_2 = Client(HTTP_HOST=site_2.hostname)

        # assert that there are now two sites rooted at main
        self.assertEqual(self.main.sites_rooted_here.count(), 2)

        # create molo form page
        molo_form_page, molo_form_field = \
            self.create_molo_form_page(
                parent=self.forms_index,
                homepage_button_text='share your story yo')

        # assert that both sites render the form
        response = client_1.get('/molo-forms-main-1/test-form/')
        self.assertEqual(response.status_code, 200)
        response = client_2.get(
            site_2.root_url + '/molo-forms-main-1/test-form/')
        self.assertEqual(response.status_code, 200)
