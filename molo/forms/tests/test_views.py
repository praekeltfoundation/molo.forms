import json
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase, RequestFactory
from django.test.client import Client
from django.utils.text import slugify
from molo.core.models import (Languages, Main, SiteLanguageRelation,
                              SiteSettings)
from molo.core.tests.base import MoloTestCaseMixin
from molo.forms.models import (
    MoloFormField,
    MoloFormPage,
    FormsIndexPage,
    PersonalisableForm,
    PersonalisableFormField
)

from .utils import skip_logic_data
from .base import (
    create_personalisable_form_page,
    create_molo_dropddown_field,
    create_personalisable_dropddown_field,
    create_molo_form_formfield,
    create_molo_form_page
)

from .constants import SEGMENT_FORM_DATA

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
        self.french = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting,
            locale='fr',
            is_active=True)

        self.section = self.mk_section(self.section_index, title='section')
        self.article = self.mk_article(self.section, title='article')

        # Create forms index pages
        self.forms_index = FormsIndexPage.objects.child_of(
            self.main).first()

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
        self.french2 = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting2,
            locale='fr',
            is_active=True)

        self.mk_main2(title='main3', slug='main3', path="00010003")
        self.client2 = Client(HTTP_HOST=self.main2.get_site().hostname)

    def create_molo_form_page_with_field(
            self, parent, display_form_directly=False,
            allow_anonymous_submissions=False, **kwargs):
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

    def test_homepage_button_text_customisable(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.forms_index,
                homepage_button_text='share your story yo')
        self.client.login(username='tester', password='tester')
        response = self.client.get('/')
        self.assertContains(response, 'share your story yo')
        self.assertNotContains(response, 'Take the Form')

    def test_correct_intro_shows_on_homepage(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.forms_index,
                homepage_button_text='share your story yo')
        self.client.login(username='tester', password='tester')
        response = self.client.get('/')
        self.assertContains(response, 'Shorter homepage introduction')
        self.assertNotContains(response, 'Take the Form')

    def test_anonymous_submissions_not_allowed_by_default(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(parent=self.section_index)

        response = self.client.get(molo_form_page.url)

        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, 'Please log in to take this form')

    def test_submit_form_as_logged_in_user(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(parent=self.section_index)

        self.client.login(username='tester', password='tester')

        response = self.client.get(molo_form_page.url)
        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, molo_form_page.introduction)
        self.assertContains(response, molo_form_field.label)
        self.assertContains(response, molo_form_page.submit_text)

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)

        self.assertContains(response, molo_form_page.thank_you_text)

        # for test_multiple_submissions_not_allowed_by_default
        return molo_form_page.url

    def test_anonymous_submissions_option(self):
        molo_form_page = create_molo_form_page(
            parent=self.forms_index,
            allow_anonymous_submissions=True)
        molo_form_field = create_molo_form_formfield(
            form=molo_form_page,
            field_type='singleline',
            label="test label")

        response = self.client.get(molo_form_page.url)
        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, molo_form_page.introduction)
        self.assertContains(response, molo_form_field.label)
        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)
        self.assertContains(response, molo_form_page.thank_you_text)

        # for test_multiple_submissions_not_allowed_by_default_anonymous
        return molo_form_page.url

    def test_multiple_submissions_not_allowed_by_default(self):
        molo_form_page_url = self.test_submit_form_as_logged_in_user()

        response = self.client.get(molo_form_page_url)

        self.assertContains(response,
                            'You have already completed this form.')

    def test_multiple_submissions_not_allowed_by_default_anonymous(self):
        molo_form_page_url = self.test_anonymous_submissions_option()

        response = self.client.get(molo_form_page_url)

        self.assertContains(response,
                            'You have already completed this form.')

    def test_multiple_submissions_option(self, anonymous=False):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.section_index,
                allow_multiple_submissions_per_user=True,
                allow_anonymous_submissions=anonymous
            )

        if not anonymous:
            self.client.login(username='tester', password='tester')

        for _ in range(2):
            response = self.client.get(molo_form_page.url)

            self.assertContains(response, molo_form_page.title)
            self.assertContains(response, molo_form_page.introduction)
            self.assertContains(response, molo_form_field.label)

            response = self.client.post(molo_form_page.url, {
                molo_form_field.label.lower().replace(' ', '-'):
                    'python'
            }, follow=True)

            self.assertContains(response, molo_form_page.thank_you_text)

    def test_multiple_submissions_option_anonymous(self):
        self.test_multiple_submissions_option(True)

    def test_show_results_option(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.section_index,
                allow_anonymous_submissions=True,
                show_results=True
            )

        response = self.client.get(molo_form_page.url)
        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, molo_form_page.introduction)
        self.assertContains(response, molo_form_field.label)

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)
        self.assertContains(response, molo_form_page.thank_you_text)
        self.assertContains(response, 'Results')
        self.assertContains(response, molo_form_field.label)
        self.assertContains(response, 'python</span> 1')

    def test_show_results_as_percentage_option(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.section_index,
                allow_anonymous_submissions=True,
                allow_multiple_submissions_per_user=True,
                show_results=True,
                show_results_as_percentage=True
            )

        response = self.client.get(molo_form_page.url)
        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, molo_form_page.introduction)
        self.assertContains(response, molo_form_field.label)

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)
        self.assertContains(response, molo_form_page.thank_you_text)
        self.assertContains(response, 'Results')
        self.assertContains(response, molo_form_field.label)
        self.assertContains(response, 'python</span> 100%')

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'java'
        }, follow=True)
        self.assertContains(response, molo_form_page.thank_you_text)
        self.assertContains(response, 'Results')
        self.assertContains(response, molo_form_field.label)
        self.assertContains(response, 'python</span> 50%')

    def test_get_result_percentages_as_json(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.section_index,
                allow_multiple_submissions_per_user=True
            )

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)
        response = self.client.get(
            '/forms/%s/results_json/' % molo_form_page.slug)
        self.assertEqual(
            response.json(), {'Your favourite animal': {'python': 100}})

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'java'
        }, follow=True)
        response = self.client.get(
            '/forms/%s/results_json/' % molo_form_page.slug)
        self.assertEqual(response.json(),
                         {'Your favourite animal': {'java': 50, 'python': 50}})
        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'java'
        }, follow=True)
        response = self.client.get(
            '/forms/%s/results_json/' % molo_form_page.slug)
        self.assertEqual(response.json(),
                         {'Your favourite animal': {'java': 67, 'python': 33}})
        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'java'
        }, follow=True)
        response = self.client.get(
            '/forms/%s/results_json/' % molo_form_page.slug)
        self.assertEqual(response.json(),
                         {'Your favourite animal': {'java': 75, 'python': 25}})

    def test_multi_step_option(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.section_index,
                allow_anonymous_submissions=True,
                multi_step=True
            )

        extra_molo_form_field = MoloFormField.objects.create(
            page=molo_form_page,
            sort_order=2,
            label='Your favourite actor',
            field_type='singleline',
            required=True
        )

        response = self.client.get(molo_form_page.url)

        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, molo_form_page.introduction)
        self.assertContains(response, molo_form_field.label)
        self.assertNotContains(response, extra_molo_form_field.label)
        self.assertContains(response, 'Next Question')

        response = self.client.post(molo_form_page.url + '?p=2', {
            molo_form_field.label.lower().replace(' ', '-'): 'python'
        })

        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, molo_form_page.introduction)
        self.assertNotContains(response, molo_form_field.label)
        self.assertContains(response, extra_molo_form_field.label)
        self.assertContains(response, molo_form_page.submit_text)

        response = self.client.post(molo_form_page.url + '?p=3', {
            extra_molo_form_field.label.lower().replace(' ', '-'):
                'Steven Seagal ;)'
        }, follow=True)

        self.assertContains(response, molo_form_page.thank_you_text)

        # for test_multi_step_multi_submissions_anonymous
        return molo_form_page.url

    def test_can_submit_after_validation_error(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.section_index,
                allow_anonymous_submissions=True
            )

        response = self.client.get(molo_form_page.url)

        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, molo_form_page.introduction)
        self.assertContains(response, molo_form_field.label)

        response = self.client.post(molo_form_page.url, {})

        self.assertContains(response, 'This field is required.')

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)

        self.assertContains(response, molo_form_page.thank_you_text)

    def test_multi_step_multi_submissions_anonymous(self):
        '''
        Tests that multiple anonymous submissions are not allowed for
        multi-step forms by default
        '''
        molo_form_page_url = self.test_multi_step_option()

        response = self.client.get(molo_form_page_url)

        self.assertContains(response,
                            'You have already completed this form.')

    def test_form_template_tag_on_home_page_specific(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(parent=self.forms_index)
        response = self.client.get("/")
        self.assertContains(response, 'Take The Form</a>')
        self.assertContains(response, molo_form_page.homepage_introduction)
        user = User.objects.create_superuser(
            username='testuser', password='password', email='test@email.com')
        self.client2.login(user=user)
        response = self.client2.get(self.site2.root_url)
        self.assertNotContains(response, 'Take The Form</a>')

    # def test_can_only_see_sites_forms_in_admin(self):
    #     molo_form_page, molo_form_field = \
    #         self.create_molo_form_page_with_field(parent=self.forms_index)
    #     response = self.client.get("/")
    #     self.assertContains(response, 'Take The Form</a>')
    #     self.assertContains(response, molo_form_page.homepage_introduction)
    #     user = User.objects.create_superuser(
    #         username='testuser', password='password', email='test@email.com')
    #     self.client2.login(user=user)
    #     response = self.client2.get(self.site2.root_url)
    #     self.assertNotContains(response, 'Take The Form</a>')
    #     self.login()
    #     response = self.client.get('/admin/forms/')
    #     self.assertContains(
    #         response,
    #         '<h2><a href="/admin/forms/submissions/%s/">'
    #         'Test Form</a></h2>' % molo_form_page.pk)
    #     user = get_user_model().objects.create_superuser(
    #         username='superuser2',
    #         email='superuser2@email.com', password='pass2')
    #     self.client2.login(username='superuser2', password='pass2')

    #     response = self.client2.get(self.site2.root_url + '/admin/forms/')
    #     self.assertNotContains(
    #         response,
    #         '<h2><a href="/admin/forms/submissions/%s/">'
    #         'Test Form</a></h2>' % molo_form_page.pk)

    def test_changing_languages_changes_form(self):
        # Create a form
        self.user = self.login()
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(parent=self.forms_index)
        # Create a translated form
        response = self.client.post(reverse(
            'add_translation', args=[molo_form_page.id, 'fr']))
        translated_form = MoloFormPage.objects.get(
            slug='french-translation-of-test-form')
        translated_form.save_revision().publish()
        create_molo_form_formfield(
            form=translated_form, field_type='singleline',
            label="Your favourite animal in french", required=True)

        # when requesting the english form with the french language code
        # it should return the french form
        request = RequestFactory().get(molo_form_page.url)
        request.LANGUAGE_CODE = 'fr'
        request.context = {'page': molo_form_page}
        request.site = self.main.get_site()
        response = molo_form_page.serve_questions(request)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['location'], translated_form.url)

    def test_changing_languages_when_no_translation_stays_on_form(self):
        setting = SiteSettings.objects.create(site=self.main.get_site())
        setting.show_only_translated_pages = True
        setting.save()

        # Create a form
        self.user = self.login()
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(parent=self.forms_index)

        # when requesting the english form with the french language code
        # it should return the english form
        request = RequestFactory().get(molo_form_page.url)
        request.LANGUAGE_CODE = 'fr'
        request.context = {'page': molo_form_page}
        request.site = self.main.get_site()
        request.session = {}
        request.user = self.user
        response = molo_form_page.serve_questions(request)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Test Form')

    def test_can_see_translated_form_submissions_in_admin(self):
        """ Test that submissions to translated forms can be seen in the
            admin
        """
        # Create a form
        self.user = self.login()
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(parent=self.forms_index)
        # Create a translated form
        response = self.client.post(reverse(
            'add_translation', args=[molo_form_page.id, 'fr']))
        translated_form = MoloFormPage.objects.get(
            slug='french-translation-of-test-form')
        translated_form.save_revision().publish()
        translated_form_field = create_molo_form_formfield(
            form=translated_form, field_type='singleline',
            label="Your favourite animal in french", required=True)

        # Check both forms are listed in the admin
        response = self.client.get('/admin/forms/')
        self.assertContains(response, 'Test Form')
        self.assertContains(response, 'French translation of Test Form')

        # Submit responses to both forms
        self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'):
                'an english answer'
        })
        self.client.post(translated_form.url, {
            translated_form_field.label.lower().replace(' ', '-'):
                'a french answer'
        })

        # Check the responses are shown on the submission pages
        response = self.client.get('/admin/forms/submissions/%s/' %
                                   molo_form_page.pk)
        self.assertContains(response, 'an english answer')
        self.assertNotContains(response, 'a french answer')
        response = self.client.get('/admin/forms/submissions/%s/' %
                                   translated_form.pk)
        self.assertNotContains(response, 'an english answer')
        self.assertContains(response, 'a french answer')

    def test_no_duplicate_indexes(self):
        self.assertTrue(FormsIndexPage.objects.child_of(self.main2).exists())
        self.assertEquals(
            FormsIndexPage.objects.child_of(self.main2).count(), 1)
        self.client.post(reverse(
            'wagtailadmin_pages:copy',
            args=(self.forms_index.pk,)),
            data={
                'new_title': 'blank',
                'new_slug': 'blank',
                'new_parent_page': self.main2,
                'copy_subpages': 'true',
                'publish_copies': 'true'})
        self.assertEquals(
            FormsIndexPage.objects.child_of(self.main2).count(), 1)

    def test_translated_form(self):
        self.user = self.login()
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(parent=self.forms_index)

        self.client.post(reverse(
            'add_translation', args=[molo_form_page.id, 'fr']))
        translated_form = MoloFormPage.objects.get(
            slug='french-translation-of-test-form')
        translated_form.save_revision().publish()

        response = self.client.get("/")
        self.assertContains(response,
                            '<h1 class="forms__title">Test Form</h1>')
        self.assertNotContains(
            response,
            '<h1 class="forms__title">French translation of Test Form</h1>'
        )

        response = self.client.get('/locale/fr/')
        response = self.client.get('/')
        self.assertNotContains(
            response,
            '<h1 class="forms__title">Test Form</h1>')
        self.assertContains(
            response,
            '<h1 class="forms__title">French translation of Test Form</h1>'
        )

    def test_form_template_tag_on_footer(self):
        self.user = self.login()
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(parent=self.forms_index)

        self.client.post(reverse(
            'add_translation', args=[molo_form_page.id, 'fr']))
        translated_form = MoloFormPage.objects.get(
            slug='french-translation-of-test-form')
        translated_form.save_revision().publish()

        response = self.client.get('/')
        self.assertContains(
            response,
            '<a href="/molo-forms-main-1/test-form/" class="footer-link"> '
            '<div class="footer-link__thumbnail-icon"> '
            '<img src="/static/img/clipboard.png" '
            'class="menu-list__item--icon" /></div> '
            '<span class="footer-link__title">Test Form', html=True)

        self.client.get('/locale/fr/')
        response = self.client.get('/')
        self.assertContains(
            response,
            '<a href="/molo-forms-main-1/french-translation-of-test-form/"'
            'class="footer-link"> <div class="footer-link__thumbnail-icon"> '
            '<img src="/static/img/clipboard.png" '
            'class="menu-list__item--icon" /></div> '
            '<span class="footer-link__title">'
            'French translation of Test Form', html=True)

    def test_form_template_tag_on_section_page(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(parent=self.section)

        response = self.client.get(self.section.url)
        self.assertContains(response, 'Take The Form</a>')
        self.assertContains(response, molo_form_page.homepage_introduction)

    def test_translated_form_on_section_page(self):
        self.user = self.login()
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(parent=self.section)

        self.client.post(reverse(
            'add_translation', args=[molo_form_page.id, 'fr']))
        translated_form = MoloFormPage.objects.get(
            slug='french-translation-of-test-form')
        translated_form.save_revision().publish()

        response = self.client.get(self.section.url)
        self.assertContains(response,
                            '<h1 class="forms__title">Test Form</h1>')
        self.assertNotContains(
            response,
            '<h1 class="forms__title">French translation of Test Form</h1>'
        )

        response = self.client.get('/locale/fr/')
        response = self.client.get(self.section.url)
        self.assertNotContains(
            response,
            '<h1 class="forms__title">Test Form</h1>')
        self.assertContains(
            response,
            '<h1 class="forms__title">French translation of Test Form</h1>'
        )

    def test_form_template_tag_on_article_page(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(parent=self.article)
        response = self.client.get(self.article.url)
        self.assertContains(response,
                            'Take The Form</a>'.format(
                                molo_form_page.url))
        self.assertContains(response, molo_form_page.homepage_introduction)

    def test_form_list_display_direct_logged_out(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.forms_index,
                display_form_directly=True)
        response = self.client.get('/')
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Please log in to take this form')
        self.assertNotContains(response, molo_form_field.label)

    def test_form_list_display_direct_logged_in(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.forms_index,
                display_form_directly=True)

        self.user = self.login()
        response = self.client.get('/')
        self.assertEquals(response.status_code, 200)
        self.assertNotContains(response, 'Please log in to take this form')
        self.assertContains(response, molo_form_field.label)

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)

        self.assertContains(response, molo_form_page.thank_you_text)

        response = self.client.get('/')
        self.assertNotContains(response, molo_form_field.label)
        self.assertContains(response,
                            'You have already completed this form.')

    def test_anonymous_submissions_option_display_direct(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.forms_index,
                display_form_directly=True,
                allow_anonymous_submissions=True,
            )

        response = self.client.get('/')

        self.assertContains(response, molo_form_field.label)
        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)
        self.assertContains(response, molo_form_page.thank_you_text)

        response = self.client.get('/')
        self.assertNotContains(response, molo_form_field.label)
        self.assertContains(response,
                            'You have already completed this form.')

    def test_multiple_submissions_display_direct(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.forms_index,
                display_form_directly=True,
                allow_multiple_submissions_per_user=True,
            )

        self.user = self.login()
        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)
        self.assertContains(response, molo_form_page.thank_you_text)

        response = self.client.get('/')
        self.assertContains(response, molo_form_field.label)
        self.assertNotContains(response,
                               'You have already completed this form.')


class TestDeleteButtonRemoved(TestCase, MoloTestCaseMixin):

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

        self.forms_index = FormsIndexPage(
            title='Security Questions',
            slug='security-questions')
        self.main.add_child(instance=self.forms_index)
        self.forms_index.save_revision().publish()

    def test_delete_btn_removed_for_forms_index_page_in_main(self):

        main_page = Main.objects.first()
        response = self.client.get('/admin/pages/{0}/'
                                   .format(str(main_page.pk)))
        self.assertEquals(response.status_code, 200)

        forms_index_page_title = (
            FormsIndexPage.objects.first().title)

        soup = BeautifulSoup(response.content, 'html.parser')
        index_page_rows = soup.find_all('tbody')[0].find_all('tr')

        for row in index_page_rows:
            if row.h2.a.string == forms_index_page_title:
                self.assertTrue(row.find('a', string='Edit'))
                self.assertFalse(row.find('a', string='Delete'))

    def test_delete_button_removed_from_dropdown_menu(self):
        forms_index_page = FormsIndexPage.objects.first()

        response = self.client.get('/admin/pages/{0}/'
                                   .format(str(forms_index_page.pk)))
        self.assertEquals(response.status_code, 200)

        delete_link = ('<a href="/admin/pages/{0}/delete/" '
                       'title="Delete this page" class="u-link '
                       'is-live ">Delete</a>'
                       .format(str(forms_index_page.pk)))
        self.assertNotContains(response, delete_link, html=True)

    def test_delete_button_removed_in_edit_menu(self):
        forms_index_page = FormsIndexPage.objects.first()

        response = self.client.get('/admin/pages/{0}/edit/'
                                   .format(str(forms_index_page.pk)))
        self.assertEquals(response.status_code, 200)

        delete_button = ('<li><a href="/admin/pages/{0}/delete/" '
                         'class="shortcut">Delete</a></li>'
                         .format(str(forms_index_page.pk)))
        self.assertNotContains(response, delete_button, html=True)


class TestSkipLogicFormView(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.mk_main()
        self.main = Main.objects.all().first()
        self.language_setting = Languages.objects.create(
            site_id=self.main.get_site().pk)
        self.english = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting,
            locale='en',
            is_active=True)

        self.molo_form_page = self.new_form('Test Form')
        self.another_molo_form_page = self.new_form('Another Test Form')

        self.last_molo_form_field = MoloFormField.objects.create(
            page=self.molo_form_page,
            sort_order=3,
            label='Your favourite actor',
            field_type='singleline',
            required=True
        )

        self.choices = ['next', 'end', 'form', 'question']
        self.skip_logic_form_field = MoloFormField.objects.create(
            page=self.molo_form_page,
            sort_order=1,
            label='Where should we go',
            field_type='dropdown',
            skip_logic=skip_logic_data(
                self.choices,
                self.choices,
                form=self.another_molo_form_page,
                question=self.last_molo_form_field,
            ),
            required=True
        )

        self.molo_form_field = MoloFormField.objects.create(
            page=self.molo_form_page,
            sort_order=2,
            label='Your favourite animal',
            field_type='singleline',
            required=True
        )

        self.another_molo_form_field = (
            MoloFormField.objects.create(
                page=self.another_molo_form_page,
                sort_order=1,
                label='Your favourite actress',
                field_type='singleline',
                required=True
            )
        )

    def new_form(self, name):
        form = MoloFormPage(
            title=name, slug=slugify(name),
            introduction='Introduction to {}...'.format(name),
            thank_you_text='Thank you for taking the {}'.format(name),
            submit_text='form submission text for {}'.format(name),
            allow_anonymous_submissions=True,
        )
        self.section_index.add_child(instance=form)
        form.save_revision().publish()
        return form

    def assertFormAndQuestions(self, response, form, questions):
        self.assertContains(response, form.title)
        self.assertContains(response, form.introduction)
        for question in questions:
            self.assertContains(response, question.label)
            self.assertContains(response, question.label)

    def test_skip_logic_next_question(self):
        response = self.client.get(self.molo_form_page.url)

        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.skip_logic_form_field]
        )
        self.assertNotContains(
            response,
            self.last_molo_form_field.label
        )
        self.assertNotContains(response, self.molo_form_field.label)
        self.assertContains(response, 'Next Question')

        response = self.client.post(self.molo_form_page.url + '?p=2', {
            self.skip_logic_form_field.clean_name: self.choices[0],
        })

        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.molo_form_field, self.last_molo_form_field]
        )
        self.assertNotContains(response, self.skip_logic_form_field.label)
        self.assertContains(response, self.molo_form_page.submit_text)

        response = self.client.post(self.molo_form_page.url + '?p=3', {
            self.molo_form_field.clean_name: 'python',
            self.last_molo_form_field.clean_name: 'Steven Seagal ;)',
        }, follow=True)

        self.assertContains(response, self.molo_form_page.thank_you_text)

    def test_skip_logic_to_end(self):
        response = self.client.get(self.molo_form_page.url)
        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.skip_logic_form_field]
        )
        self.assertNotContains(
            response,
            self.last_molo_form_field.label,
        )
        self.assertNotContains(response, self.molo_form_field.label)
        self.assertContains(response, 'Next Question')

        response = self.client.post(self.molo_form_page.url + '?p=2', {
            self.skip_logic_form_field.clean_name: self.choices[1],
        }, follow=True)

        # Should end the form and not complain about required
        # field for the last field

        self.assertContains(response, self.molo_form_page.title)
        self.assertNotContains(response, self.molo_form_field.label)
        self.assertNotContains(
            response,
            self.last_molo_form_field.label
        )
        self.assertNotContains(response, self.molo_form_page.submit_text)
        self.assertContains(response, self.molo_form_page.thank_you_text)

    def test_skip_logic_to_another_form(self):
        response = self.client.get(self.molo_form_page.url)

        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.skip_logic_form_field]
        )
        self.assertNotContains(
            response,
            self.last_molo_form_field.label
        )
        self.assertNotContains(response, self.molo_form_field.label)
        self.assertContains(response, 'Next Question')

        response = self.client.post(self.molo_form_page.url + '?p=2', {
            self.skip_logic_form_field.clean_name: self.choices[2],
        }, follow=True)

        # Should end the form and progress to the new form
        self.assertFormAndQuestions(
            response,
            self.another_molo_form_page,
            [self.another_molo_form_field],
        )

    def test_skip_logic_to_another_question(self):
        response = self.client.get(self.molo_form_page.url)

        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.skip_logic_form_field]
        )
        self.assertNotContains(
            response,
            self.last_molo_form_field.label,
        )
        self.assertNotContains(response, self.molo_form_field.label)
        self.assertContains(response, 'Next Question')

        response = self.client.post(self.molo_form_page.url + '?p=2', {
            self.skip_logic_form_field.clean_name: self.choices[3],
        }, follow=True)

        # Should end the form and progress to the new form
        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.last_molo_form_field],
        )

    def test_skip_logic_checkbox_with_data(self):
        self.skip_logic_form_field.field_type = 'checkbox'
        self.skip_logic_form_field.skip_logic = skip_logic_data(
            ['', ''],
            self.choices[:2],
        )
        self.skip_logic_form_field.save()

        response = self.client.get(self.molo_form_page.url)

        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.skip_logic_form_field]
        )
        self.assertNotContains(
            response,
            self.last_molo_form_field.label,
        )
        self.assertNotContains(response, self.molo_form_field.label)
        self.assertContains(response, 'Next Question')

        response = self.client.post(self.molo_form_page.url + '?p=2', {
            self.skip_logic_form_field.clean_name: 'on',
        }, follow=True)

        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.molo_form_field, self.last_molo_form_field]
        )
        self.assertNotContains(response, self.skip_logic_form_field.label)
        self.assertContains(response, self.molo_form_page.submit_text)

        response = self.client.post(self.molo_form_page.url + '?p=3', {
            self.molo_form_field.clean_name: 'python',
            self.last_molo_form_field.clean_name: 'Steven Seagal ;)',
        }, follow=True)

        self.assertContains(response, self.molo_form_page.thank_you_text)

    def test_skip_logic_checkbox_no_data(self):
        self.skip_logic_form_field.field_type = 'checkbox'
        self.skip_logic_form_field.skip_logic = skip_logic_data(
            ['', ''],
            self.choices[:2],
        )
        self.skip_logic_form_field.save()

        response = self.client.get(self.molo_form_page.url)

        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.skip_logic_form_field]
        )
        self.assertNotContains(
            response,
            self.last_molo_form_field.label,
        )
        self.assertNotContains(response, self.molo_form_field.label)
        self.assertContains(response, 'Next Question')

        # Unchecked textboxes have no data sent to the backend
        # Data cannot be empty as we will be submitting the csrf token
        response = self.client.post(
            self.molo_form_page.url + '?p=2',
            {'csrf': 'dummy'},
            follow=True,
        )

        self.assertContains(response, self.molo_form_page.title)
        self.assertNotContains(response, self.molo_form_field.label)
        self.assertNotContains(
            response,
            self.last_molo_form_field.label
        )
        self.assertNotContains(response, self.molo_form_page.submit_text)
        self.assertContains(response, self.molo_form_page.thank_you_text)

    def test_skip_logic_missed_required_with_checkbox(self):
        self.skip_logic_form_field.field_type = 'checkbox'
        self.skip_logic_form_field.skip_logic = skip_logic_data(
            ['', ''],
            [self.choices[3], self.choices[2]],  # question, form
            form=self.another_molo_form_page,
            question=self.last_molo_form_field,
        )
        self.skip_logic_form_field.save()

        # Skip a required question
        response = self.client.post(
            self.molo_form_page.url + '?p=2',
            {self.skip_logic_form_field.clean_name: 'on'},
            follow=True,
        )

        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.last_molo_form_field]
        )
        self.assertNotContains(response, self.skip_logic_form_field.label)
        self.assertNotContains(response, self.molo_form_field.label)
        self.assertContains(response, self.molo_form_page.submit_text)

        # Dont answer last required question: trigger error messages
        response = self.client.post(
            self.molo_form_page.url + '?p=3',
            {self.last_molo_form_field.clean_name: ''},
            follow=True,
        )

        # Go back to the same page with validation errors showing
        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.last_molo_form_field]
        )
        self.assertContains(response, 'required')
        self.assertNotContains(response, self.skip_logic_form_field.label)
        self.assertNotContains(response, self.molo_form_field.label)
        self.assertContains(response, self.molo_form_page.submit_text)

    def test_skip_logic_required_with_radio_button_field(self):
        self.user = User.objects.create_user(
            username='tester',
            email='tester@example.com',
            password='tester')
        self.client.login(username='tester', password='tester')
        form = MoloFormPage(
            title='Test Form With Redio Button',
            slug='testw-form-with-redio-button',
        )

        another_form = MoloFormPage(
            title='Anotherw Test Form',
            slug='anotherw-test-form',
        )
        self.section_index.add_child(instance=form)
        form.save_revision().publish()
        self.section_index.add_child(instance=another_form)
        another_form.save_revision().publish()

        field_choices = ['next', 'end']

        third_field = MoloFormField.objects.create(
            page=form,
            sort_order=4,
            label='A random animal',
            field_type='dropdown',
            skip_logic=skip_logic_data(
                field_choices,
                field_choices,
            ),
            required=True
        )
        first_field = MoloFormField.objects.create(
            page=form,
            sort_order=1,
            label='Your other favourite animal',
            field_type='radio',
            skip_logic=skip_logic_data(
                field_choices + ['question', 'form'],
                field_choices + ['question', 'form'],
                question=third_field,
                form=another_form,
            ),
            required=True
        )
        second_field = MoloFormField.objects.create(
            page=form,
            sort_order=2,
            label='Your favourite animal',
            field_type='dropdown',
            skip_logic=skip_logic_data(
                field_choices,
                field_choices,
            ),
            required=True
        )

        response = self.client.post(
            form.url + '?p=2',
            {another_form: ''},
            follow=True,
        )
        self.assertContains(response, 'required')
        self.assertNotContains(response, second_field.label)
        self.assertContains(response, first_field.label)


class TestPositiveNumberView(TestCase, MoloTestCaseMixin):
    def setUp(self):
        self.mk_main()
        self.main = Main.objects.all().first()
        self.language_setting = Languages.objects.create(
            site_id=self.main.get_site().pk)
        self.english = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting,
            locale='en',
            is_active=True)

        self.forms_index = FormsIndexPage(
            title='Molo Forms',
            slug='molo-forms')
        self.main.add_child(instance=self.forms_index)
        self.forms_index.save_revision().publish()

    def test_positive_number_field_validation(self):
        self.user = User.objects.create_user(
            username='tester',
            email='tester@example.com',
            password='tester')
        self.client.login(username='tester', password='tester')
        form = MoloFormPage(
            title='Test Form With Positive Number',
            slug='testw-form-with-positive-number',
            thank_you_text='Thank you for taking the form',
        )
        self.forms_index.add_child(instance=form)
        form.save_revision().publish()

        positive_number_field = MoloFormField.objects.create(
            page=form,
            sort_order=1,
            label='Your lucky number?',
            field_type='positive_number',
            required=True
        )

        response = self.client.post(
            form.url + '?p=2',
            {positive_number_field.clean_name: '-1'},
            follow=True,
        )

        self.assertContains(response, positive_number_field.label)
        self.assertContains(
            response, 'Ensure this value is greater than or equal to 0')

        response = self.client.post(
            form.url + '?p=2',
            {positive_number_field.clean_name: '1'},
            follow=True,
        )

        self.assertContains(
            response, form.thank_you_text)


class SegmentCountView(TestCase, MoloTestCaseMixin):

    def setUp(self):
        self.mk_main()
        self.user = User.objects.create_user(
            username='tester', email='tester@example.com', password='tester')
        # Create form
        self.personalisable_form = PersonalisableForm(title='Test Form')
        FormsIndexPage.objects.first().add_child(
            instance=self.personalisable_form
        )
        self.personalisable_form.save_revision()
        PersonalisableFormField.objects.create(
            field_type='singleline', label='Singleline Text',
            page=self.personalisable_form
        )

    def submit_form(self, form, user):
        submission = form.get_submission_class()
        data = {field.clean_name: 'super random text'
                for field in form.get_form_fields()}
        submission.objects.create(user=user, page=self.personalisable_form,
                                  form_data=json.dumps(data))

    # def test_segment_user_count(self):
    #     self.submit_form(self.personalisable_form, self.user)
    #     response = self.client.post('/forms/count/', SEGMENT_FORM_DATA)

    #     self.assertDictEqual(response.json(), {"segmentusercount": 1})

    def test_segment_user_count_returns_errors(self):
        self.submit_form(self.personalisable_form, self.user)
        data = SEGMENT_FORM_DATA
        data['name'] = [""]
        data['forms_formresponserule_related-0-form'] = ['20']
        response = self.client.post('/forms/count/', data)

        self.assertDictEqual(response.json(), {"errors": {
            "forms_formresponserule_related-0-form": [
                "Select a valid choice. That choice is not one of the "
                "available choices."],
            "name": ["This field is required."]}})


class TestPollsViaFormsView(TestCase, MoloTestCaseMixin):

    """
    Tests to check if polls are not
    being paginated when they include fields with skip_logic_data.
    Also test that page_break is not causing any pagination on the forms
    """
    def setUp(self):
        self.mk_main()
        self.choices = ['next', 'end', 'form']
        self.forms_index = FormsIndexPage.objects.first()

    def test_molo_poll(self):
        form = create_molo_form_page(
            self.forms_index, display_form_directly=True)
        drop_down_field = create_molo_dropddown_field(
            self.forms_index, form, self.choices)
        response = self.client.post(
            form.url + '?p=1',
            {drop_down_field.clean_name: 'next'},
            follow=True,
        )
        self.assertContains(response, form.thank_you_text)
        self.assertNotContains(response, 'That page number is less than 1')

    def test_molo_poll_with_page_break(self):
        form = create_molo_form_page(
            self.forms_index, display_form_directly=True)
        drop_down_field = create_molo_dropddown_field(
            self.forms_index, form, self.choices, page_break=True)
        response = self.client.post(
            form.url + '?p=1',
            {drop_down_field.clean_name: 'next'},
            follow=True,
        )
        self.assertContains(response, form.thank_you_text)
        self.assertNotContains(response, 'That page number is less than 1')

    def test_personalisable_form_poll(self):
        form = create_personalisable_form_page(
            self.forms_index,
            display_form_directly=True)
        drop_down_field = create_personalisable_dropddown_field(
            self.forms_index, form, self.choices)
        response = self.client.post(
            form.url + '?p=1',
            {drop_down_field.clean_name: 'next'},
            follow=True,
        )
        self.assertContains(response, form.thank_you_text)
        self.assertNotContains(response, 'That page number is less than 1')

    def test_personalisable_form_poll_with_page_break(self):
        form = create_personalisable_form_page(
            self.forms_index, display_form_directly=True)
        drop_down_field = create_personalisable_dropddown_field(
            self.forms_index, form, self.choices, page_break=True)
        response = self.client.post(
            form.url + '?p=1',
            {drop_down_field.clean_name: 'next'},
            follow=True,
        )
        self.assertContains(response, form.thank_you_text)
        self.assertNotContains(response, 'That page number is less than 1')
