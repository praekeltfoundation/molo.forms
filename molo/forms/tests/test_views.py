import json
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.test import TestCase, RequestFactory
from django.test.client import Client
from django.utils.text import slugify
from molo.core.models import (Languages, Main, SiteLanguageRelation,
                              SiteSettings)
from molo.core.tests.base import MoloTestCaseMixin
from molo.forms.templatetags.molo_forms_tags import url_to_anchor
from molo.forms.models import (
    MoloFormField,
    MoloFormPage,
    FormsIndexPage,
    ArticlePageForms,
    MoloFormSubmission,
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
            self.create_molo_form_page_with_field(
                parent=self.section_index,
                thank_you_text='https://abc.com/123?')

        self.client.login(username='tester', password='tester')

        response = self.client.get(molo_form_page.url)
        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, molo_form_page.introduction)
        self.assertContains(response, molo_form_field.label)
        self.assertContains(response, molo_form_page.submit_text)

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '_'): 'python',
        }, follow=True)
        self.assertContains(
            response, url_to_anchor(molo_form_page.thank_you_text))

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
            molo_form_field.label.lower().replace(' ', '_'): 'python'
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
                molo_form_field.label.lower().replace(' ', '_'):
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
            molo_form_field.label.lower().replace(' ', '_'): 'python'
        }, follow=True)
        self.assertContains(response, molo_form_page.thank_you_text)
        self.assertContains(response, 'Results')
        self.assertContains(response, molo_form_field.label)
        self.assertContains(response, 'python</span> 1')

    def test_show_results_option_ajax(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.section_index,
                allow_anonymous_submissions=True,
                show_results=True,
            )

        response = self.client.get(molo_form_page.url)
        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, molo_form_page.introduction)
        self.assertContains(response, molo_form_field.label)
        response = self.client.post(molo_form_page.get_full_url(), {
            "ajax": 'True',
            molo_form_field.label.lower().replace(' ', '_'): 'python',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.content,
            b'{"Your favourite animal": {"python": 1}}'
        )

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
            molo_form_field.label.lower().replace(' ', '_'): 'python'
        }, follow=True)
        self.assertContains(response, molo_form_page.thank_you_text)
        self.assertContains(response, 'Results')
        self.assertContains(response, molo_form_field.label)
        self.assertContains(response, 'python</span> 100%')

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '_'): 'java'
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
            molo_form_field.label.lower().replace(' ', '_'): 'python'
        }, follow=True)
        response = self.client.get(
            '/forms/%s/results_json/' % molo_form_page.slug)
        self.assertEqual(
            response.json(), {'Your favourite animal': {'python': 100}})

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '_'): 'java'
        }, follow=True)
        response = self.client.get(
            '/forms/%s/results_json/' % molo_form_page.slug)
        self.assertEqual(response.json(),
                         {'Your favourite animal': {'java': 50, 'python': 50}})
        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '_'): 'java'
        }, follow=True)
        response = self.client.get(
            '/forms/%s/results_json/' % molo_form_page.slug)
        self.assertEqual(response.json(),
                         {'Your favourite animal': {'java': 67, 'python': 33}})
        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '_'): 'java'
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
            molo_form_field.label.lower().replace(' ', '_'): 'python'
        })

        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, molo_form_page.introduction)
        self.assertNotContains(response, molo_form_field.label)
        self.assertContains(response, extra_molo_form_field.label)
        self.assertContains(response, molo_form_page.submit_text)

        response = self.client.post(molo_form_page.url + '?p=3', {
            extra_molo_form_field.label.lower().replace(' ', '_'):
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
            molo_form_field.label.lower().replace(' ', '_'): 'python'
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

    def test_can_only_see_sites_forms_in_admin(self):
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
        self.login()
        response = self.client.get('/admin/forms/')
        self.assertContains(
            response,
            '<a href="/admin/forms/submissions/%s/">'
            'Test Form</a>' % molo_form_page.pk)
        get_user_model().objects.create_superuser(
            username='superuser2',
            email='superuser2@email.com', password='pass2')
        self.client2.login(username='superuser2', password='pass2')

        response = self.client2.get(self.site2.root_url + '/admin/forms/')
        self.assertNotContains(
            response,
            '<h2><a href="/admin/forms/submissions/%s/">'
            'Test Form</a></h2>' % molo_form_page.pk)

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
        request._wagtail_site = self.main.get_site()
        response = molo_form_page.serve_questions(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['location'], translated_form.url)

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
        request.session = {}
        request.user = self.user
        request._wagtail_site = self.main.get_site()
        response = molo_form_page.serve_questions(request)
        self.assertEqual(response.status_code, 200)
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
            molo_form_field.label.lower().replace(' ', '_'):
                'an english answer'
        })
        self.client.post(translated_form.url, {
            translated_form_field.label.lower().replace(' ', '_'):
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
        self.assertEqual(
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
        self.assertEqual(
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
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please log in to take this form')
        self.assertNotContains(response, molo_form_field.label)

    def test_form_list_display_direct_logged_in(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page_with_field(
                parent=self.forms_index,
                display_form_directly=True)

        self.user = self.login()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Please log in to take this form')
        self.assertContains(response, molo_form_field.label)

        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '_'): 'python'
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
            molo_form_field.label.lower().replace(' ', '_'): 'python'
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
            molo_form_field.label.lower().replace(' ', '_'): 'python'
        }, follow=True)
        self.assertContains(response, molo_form_page.thank_you_text)

        response = self.client.get('/')
        self.assertContains(response, molo_form_field.label)
        self.assertNotContains(response,
                               'You have already completed this form.')

    def test_hidden_form_field(self):
        self.client.force_login(self.user)
        form = create_molo_form_page(
            self.forms_index, display_form_directly=True)
        hidden_field = create_molo_form_formfield(
            form, 'hidden', 'some hidden field')
        req = RequestFactory()
        req.user = self.user
        req.site = self.site
        response = self.client.get(form.url, request=req)
        self.assertNotContains(response, hidden_field.label)
        self.assertContains(
            response,
            '<input type="hidden" name="some_hidden_field" '
            'id="id_some_hidden_field">'
        )

    def test_article_form_submissions(self):
        """
        with an article page
        """
        form = create_molo_form_page(
            self.forms_index,
            title='test form',
            display_form_directly=True,
            save_article_object=True,
            allow_anonymous_submissions=True,
        )
        field = create_molo_form_formfield(form, 'singleline')
        hidden_field = create_molo_form_formfield(
            form, 'hidden', label="hidden_field lets check it out")
        ArticlePageForms.objects.create(page=self.article, form=form)

        url = self.article.get_full_url()
        article_field = 'name="article_page" value="{}"' \
            .format(self.article.pk)

        # Get an article with a related form page
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn(bytes(field.label, encoding='utf-8'), res.content)
        self.assertIn(bytes(article_field, encoding='utf-8'), res.content)
        self.assertIn(bytes(hidden_field.label, encoding='utf-8'), res.content)
        self.assertIn(bytes(self.article.title, encoding='utf-8'), res.content)

        url = form.get_full_url()
        data = {
            'article_page': self.article.pk,
            field.clean_name: 'abc',
        }
        # Post: Respond to  form related to article
        res = self.client.post(url, data=data)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(
            res.url,
            '/forms/test-form/{}/success/'.format(self.article.pk)
        )
        self.assertTrue(
            MoloFormSubmission.objects.filter(
                article_page=self.article).exists()
        )

    def test_article_form_result_calculations(self):
        """
        with an article page
        """
        form = create_molo_form_page(
            self.forms_index,
            title='test form',
            display_form_directly=True,
            show_results=True,
            save_article_object=True,
            allow_anonymous_submissions=True,
        )
        article = self.mk_article(self.section, title='article 2')
        field = MoloFormField.objects.create(
            page=form, label='a, b or c?', field_type='singleline')

        ArticlePageForms.objects.create(page=article, form=form)
        ArticlePageForms.objects.create(page=self.article, form=form)
        form_data = {field.clean_name: 'a', 'article_page': article.pk}
        MoloFormSubmission.objects.create(
            page=form, article_page=article, form_data=json.dumps(form_data))

        form_data.update({'article_page': self.article.pk})
        success_url = reverse('molo.forms:success_article_form', kwargs={
            'slug': form.slug, 'article': self.article.pk})

        results = self.client.post(form.get_full_url(), data=form_data)
        self.assertEqual(results.status_code, 302)
        self.assertEqual(results.url, success_url)

        results = self.client.get(success_url)
        self.assertEqual(results.status_code, 200)
        self.assertTemplateUsed(results, 'forms/molo_form_page_success.html')
        self.assertIn(
            '<span>a</span> 1', str(results.content)
        )

        form.show_results_as_percentage = True
        form.save()

        results = self.client.get(success_url)
        self.assertEqual(results.status_code, 200)
        self.assertTemplateUsed(results, 'forms/molo_form_page_success.html')
        self.assertIn(
            '<span>a</span> 100%', str(results.content)
        )
        self.assertNotIn(
            'article_page', str(results.content)
        )

    def test_article_form_result_calculations_ajax(self):
        """
        with an article page
        """
        form = create_molo_form_page(
            self.forms_index,
            title='test form',
            display_form_directly=True,
            show_results=True,
            save_article_object=True,
            allow_anonymous_submissions=True,
        )
        article = self.mk_article(self.section, title='article 2')
        field = MoloFormField.objects.create(
            page=form, label='a, b or c?', field_type='singleline')

        ArticlePageForms.objects.create(page=article, form=form)
        ArticlePageForms.objects.create(page=self.article, form=form)

        form_data = {field.clean_name: 'a', 'article_page': article.pk}
        MoloFormSubmission.objects.create(
            page=form, article_page=article, form_data=json.dumps(form_data))

        form_data.update({'article_page': self.article.pk})

        success_url = reverse('molo.forms:success_article_form', kwargs={
            'slug': form.slug, 'article': self.article.pk})

        results = self.client.post(form.get_full_url(), data=form_data)
        self.assertEqual(results.status_code, 302)
        self.assertEqual(results.url, success_url)

        results = self.client.get(success_url + '?format=json')
        self.assertEqual(results.status_code, 200)
        self.assertEqual(
            json.loads('{"a, b or c?": {"a": 1}, "article_page": {"%d": 1}}'
                       % self.article.pk),
            results.json()
        )

        form.show_results_as_percentage = True
        form.save()

        results = self.client.get(success_url + '?format=json')
        self.assertEqual(results.status_code, 200)
        self.assertEqual(
            json.loads(
                '{"a, b or c?": {"a": 100}, "article_page": {"%d": 100}}'
                % self.article.pk
            ),
            results.json()
        )


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
        self.assertEqual(response.status_code, 200)

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
        self.assertEqual(response.status_code, 200)

        delete_link = ('<a href="/admin/pages/{0}/delete/" '
                       'title="Delete this page" class="u-link '
                       'is-live ">Delete</a>'
                       .format(str(forms_index_page.pk)))
        self.assertNotContains(response, delete_link, html=True)

    def test_delete_button_removed_in_edit_menu(self):
        forms_index_page = FormsIndexPage.objects.first()

        response = self.client.get('/admin/pages/{0}/edit/'
                                   .format(str(forms_index_page.pk)))
        self.assertEqual(response.status_code, 200)

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
            sort_order=2,
            label='Your favourite actor',
            field_type='singleline',
            required=True,
            page_break=True
        )

        self.choices = ['next', 'end', 'form', 'question']
        self.skip_logic_form_field = MoloFormField.objects.create(
            page=self.molo_form_page,
            sort_order=0,
            label='Where should we go',
            field_type='dropdown',
            skip_logic=skip_logic_data(
                self.choices,
                self.choices,
                form=self.another_molo_form_page,
                question=self.last_molo_form_field,
            ),
            required=True,
            page_break=True
        )

        self.molo_form_field = MoloFormField.objects.create(
            page=self.molo_form_page,
            sort_order=1,
            label='Your favourite animal',
            field_type='singleline',
            required=True,
            page_break=False
        )

        self.another_molo_form_field = (
            MoloFormField.objects.create(
                page=self.another_molo_form_page,
                sort_order=0,
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

    def test_skip_logic_to_question_without_skipped_page_breaks(self):
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

        self.assertNotContains(response, self.skip_logic_form_field.label)
        self.assertNotContains(response, self.molo_form_field.label)

        # Should show the last question
        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.last_molo_form_field],
        )

        response = self.client.post(self.molo_form_page.url + '?p=3', {
            self.last_molo_form_field.clean_name: "frank",
        }, follow=True)

        self.assertContains(response, self.molo_form_page.thank_you_text)
        subs = self.molo_form_page.get_submission_class().objects.all()
        self.assertEqual(len(subs), 1)
        self.assertEqual(json.loads(subs[0].form_data), {
            "where_should_we_go": "question",
            "your_favourite_animal": "NA (Skipped)",
            "your_favourite_actor": "frank"})

    def test_skip_logic_to_question_with_one_skipped_page_break(self):
        self.molo_form_field.page_break = True
        self.molo_form_field.save()

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

        self.assertNotContains(response, self.skip_logic_form_field.label)
        self.assertNotContains(response, self.molo_form_field.label)

        # Should show the last question
        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.last_molo_form_field],
        )

        response = self.client.post(self.molo_form_page.url + '?p=3', {
            self.last_molo_form_field.clean_name: "frank",
        }, follow=True)

        self.assertContains(response, self.molo_form_page.thank_you_text)
        subs = self.molo_form_page.get_submission_class().objects.all()
        self.assertEqual(len(subs), 1)
        self.assertEqual(json.loads(subs[0].form_data), {
            "where_should_we_go": "question",
            "your_favourite_animal": "NA (Skipped)",
            "your_favourite_actor": "frank"})

    def test_skip_logic_to_question_with_multiple_skipped_page_breaks(self):
        self.molo_form_field.page_break = True
        self.molo_form_field.save()
        # add another form field to skip over
        self.extra_form_field = MoloFormField.objects.create(
            page=self.molo_form_page,
            sort_order=2,
            label='extra question',
            field_type='singleline',
            required=True,
            page_break=True
        )
        # Move the last question down and make sure the skip logic points to it
        self.last_molo_form_field.sort_order = 3
        self.last_molo_form_field.save()
        self.skip_logic_form_field.skip_logic = skip_logic_data(
            self.choices,
            self.choices,
            form=self.another_molo_form_page,
            question=self.last_molo_form_field,
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
            self.skip_logic_form_field.clean_name: self.choices[3],
        }, follow=True)

        self.assertNotContains(response, self.skip_logic_form_field.label)
        self.assertNotContains(response, self.molo_form_field.label)
        self.assertNotContains(response, self.extra_form_field.label)

        # Should show the last question
        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.last_molo_form_field],
        )

        response = self.client.post(self.molo_form_page.url + '?p=3', {
            self.last_molo_form_field.clean_name: "frank",
        }, follow=True)

        self.assertContains(response, self.molo_form_page.thank_you_text)
        subs = self.molo_form_page.get_submission_class().objects.all()
        self.assertEqual(len(subs), 1)
        self.assertEqual(json.loads(subs[0].form_data), {
            "where_should_we_go": "question",
            "your_favourite_animal": "NA (Skipped)",
            "extra_question": "NA (Skipped)",
            "your_favourite_actor": "frank"})

    def test_skip_logic_doesnt_repeat_pages_if_prev_pages_skipped(self):
        # The previous method of calculating page breaks led to later
        # pages being displayed multiple times

        self.molo_form_field.page_break = True
        self.molo_form_field.save()

        # add another question after the one we skip to
        self.extra_form_field = MoloFormField.objects.create(
            page=self.molo_form_page,
            sort_order=3,
            label='extra question',
            field_type='singleline',
            required=True,
            page_break=True
        )

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

        self.assertNotContains(response, self.skip_logic_form_field.label)
        self.assertNotContains(response, self.molo_form_field.label)

        # Should show the question we skipped to
        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.last_molo_form_field],
        )

        response = self.client.post(self.molo_form_page.url + '?p=3', {
            self.last_molo_form_field.clean_name: "frank",
        }, follow=True)

        self.assertNotContains(response, self.last_molo_form_field.label)

        # Should show the extra question
        self.assertFormAndQuestions(
            response,
            self.molo_form_page,
            [self.extra_form_field],
        )

        response = self.client.post(self.molo_form_page.url + '?p=4', {
            self.extra_form_field.clean_name: "answered",
        }, follow=True)

        self.assertContains(response, self.molo_form_page.thank_you_text)
        subs = self.molo_form_page.get_submission_class().objects.all()
        self.assertEqual(len(subs), 1)
        self.assertEqual(json.loads(subs[0].form_data), {
            "where_should_we_go": "question",
            "your_favourite_animal": "NA (Skipped)",
            "extra_question": "answered",
            "your_favourite_actor": "frank"})

    def test_skip_logic_checkbox_with_data(self):
        self.skip_logic_form_field.field_type = 'checkbox'
        self.skip_logic_form_field.skip_logic = skip_logic_data(
            ['', ''],
            self.choices[:2],  # next, end
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
            self.choices[:2],  # next, end
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

    def test_segment_user_count(self):
        self.submit_form(self.personalisable_form, self.user)
        data = SEGMENT_FORM_DATA
        data['forms_formresponserule_related-0-form'] \
            = [self.personalisable_form.pk]
        response = self.client.post('/forms/count/', SEGMENT_FORM_DATA)
        self.assertDictEqual(response.json(), {"segmentusercount": 1})

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
        cache.clear()
        self.mk_main()
        self.choices = ['next', 'end', 'form']
        self.forms_index = FormsIndexPage.objects.first()

    def test_molo_poll(self):
        form = create_molo_form_page(
            self.forms_index, display_form_directly=True)
        drop_down_field = create_molo_dropddown_field(
            self.forms_index, form, self.choices)
        self.client.get('/')
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


class TestAPIEndpointsView(TestCase, MoloTestCaseMixin):
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

        self.choices = ['Haley', 'Brad', 'Tom', 'Idris']
        self.form_field_1 = MoloFormField.objects.create(
            page=self.molo_form_page,
            sort_order=1,
            label='Your favourite actor',
            field_type='dropdown',
            skip_logic=skip_logic_data(
                self.choices,
            ),
            required=True
        )

        self.form_field_2 = MoloFormField.objects.create(
            page=self.molo_form_page,
            sort_order=2,
            label='Your favourite animal',
            field_type='singleline',
            required=False
        )

        self.choices = ['Red', 'Blue', 'Green', 'Yellow']
        self.form_field_3 = (
            MoloFormField.objects.create(
                page=self.molo_form_page,
                sort_order=3,
                label='Your favourite colour',
                field_type='radio',
                skip_logic=skip_logic_data(
                    self.choices,
                ),
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

    def test_article_page_api_returns_linked_forms(self):
        section = self.mk_section(self.section_index, title='section')
        article = self.mk_article(section, title='article')
        form = self.new_form("Article Form")
        article_page_form = ArticlePageForms(form=form, page=article)
        article.forms.add(article_page_form)
        article.save_revision().publish()
        response = self.client.get('/api/v2/pages/%s/' % article.id)

        obj = response.json()
        self.assertIn("forms", obj)
        self.assertEqual(len(obj['forms']), 1)
        self.assertEqual(obj['forms'][0]['form']['id'], form.id)

    def test_api_list_endpoint_shows_forms(self):
        response = self.client.get('/api/v2/forms/')

        obj = response.json()
        self.assertIn("meta", obj)
        self.assertEqual(obj["meta"]["total_count"], 2)
        self.assertEqual(obj["items"][0]["id"], self.molo_form_page.id)
        self.assertEqual(obj["items"][0]["title"], self.molo_form_page.title)
        self.assertEqual(obj["items"][1]["id"], self.another_molo_form_page.id)
        self.assertEqual(obj["items"][1]["title"],
                         self.another_molo_form_page.title)

    def test_api_list_endpoint_can_filter_by_live(self):
        self.another_molo_form_page.live = False
        self.another_molo_form_page.save()
        response = self.client.get('/api/v2/forms/?live=true')

        obj = response.json()
        self.assertIn("meta", obj)
        self.assertEqual(obj["meta"]["total_count"], 1)
        self.assertEqual(obj["items"][0]["id"], self.molo_form_page.id)
        self.assertEqual(obj["items"][0]["title"], self.molo_form_page.title)

    def test_list_endpoint_can_filter_by_allowing_anonymous_submissions(self):
        self.another_molo_form_page.allow_anonymous_submissions = False
        self.another_molo_form_page.save()
        response = self.client.get(
            '/api/v2/forms/?allow_anonymous_submissions=true')

        obj = response.json()
        self.assertIn("meta", obj)
        self.assertEqual(obj["meta"]["total_count"], 1)
        self.assertEqual(obj["items"][0]["id"], self.molo_form_page.id)
        self.assertEqual(obj["items"][0]["title"], self.molo_form_page.title)

    def test_api_list_endpoint_excludes_personalisable_forms(self):
        personalisable_form = PersonalisableForm(title='Test Form')
        FormsIndexPage.objects.first().add_child(
            instance=personalisable_form
        )
        personalisable_form.save_revision()
        response = self.client.get('/api/v2/forms/')

        obj = response.json()
        self.assertIn("meta", obj)
        self.assertEqual(obj["meta"]["total_count"], 2)
        self.assertEqual(obj["items"][0]["id"], self.molo_form_page.id)
        self.assertEqual(obj["items"][0]["title"], self.molo_form_page.title)
        self.assertEqual(obj["items"][1]["id"], self.another_molo_form_page.id)
        self.assertEqual(obj["items"][1]["title"],
                         self.another_molo_form_page.title)

    def test_api_detail_endpoint(self):
        response = self.client.get(
            '/api/v2/forms/%s/' % self.molo_form_page.id)

        obj = response.json()
        self.assertEqual(obj["title"], self.molo_form_page.title)
        self.assertEqual(len(obj["form_fields"]["items"]), 3)
        form_fields = obj["form_fields"]["items"]
        # Check fields
        self.assertEqual(form_fields[0]["sort_order"],
                         self.form_field_1.sort_order)
        self.assertEqual(form_fields[0]["label"], self.form_field_1.label)
        self.assertEqual(form_fields[0]["required"], True)
        self.assertEqual(form_fields[0]["admin_label"],
                         self.form_field_1.admin_label)
        self.assertEqual(form_fields[0]["choices"], self.form_field_1.choices)
        self.assertEqual(form_fields[0]["field_type"],
                         self.form_field_1.field_type)
        self.assertEqual(form_fields[0]["input_name"],
                         self.form_field_1.clean_name)

        self.assertEqual(form_fields[1]["sort_order"],
                         self.form_field_2.sort_order)
        self.assertEqual(form_fields[1]["label"], self.form_field_2.label)
        self.assertEqual(form_fields[1]["required"], False)
        self.assertEqual(form_fields[1]["admin_label"],
                         self.form_field_2.admin_label)
        self.assertEqual(form_fields[1]["choices"], self.form_field_2.choices)
        self.assertEqual(form_fields[1]["field_type"],
                         self.form_field_2.field_type)
        self.assertEqual(form_fields[1]["input_name"],
                         self.form_field_2.clean_name)

        self.assertEqual(form_fields[2]["sort_order"],
                         self.form_field_3.sort_order)
        self.assertEqual(form_fields[2]["label"], self.form_field_3.label)
        self.assertEqual(form_fields[2]["required"], True)
        self.assertEqual(form_fields[2]["admin_label"],
                         self.form_field_3.admin_label)
        self.assertEqual(form_fields[2]["choices"], self.form_field_3.choices)
        self.assertEqual(form_fields[2]["field_type"],
                         self.form_field_3.field_type)
        self.assertEqual(form_fields[2]["input_name"],
                         self.form_field_3.clean_name)

    def test_submit_form_endpoint_creates_a_submission(self):
        data = {self.form_field_1.clean_name: "Tom",
                self.form_field_2.clean_name: "cat",
                self.form_field_3.clean_name: "Yellow"}
        response = self.client.post(
            '/api/v2/forms/%s/submit_form/' % self.molo_form_page.id,
            data,
            format="json",
            content_type="application/json")

        self.assertEqual(response.status_code, 201)
        submissions = self.molo_form_page.get_submission_class().objects.all()
        self.assertEqual(len(submissions), 1)
        form_data = json.loads(submissions[0].form_data)
        self.assertEqual(form_data, data)

    def test_submit_form_endpoint_with_uuid_saves_for_new_user(self):
        self.assertEqual(User.objects.count(), 0)

        data = {self.form_field_1.clean_name: "Tom",
                self.form_field_2.clean_name: "cat",
                self.form_field_3.clean_name: "Yellow"}
        post_data = {"uuid": "some-uuid"}
        post_data.update(data)

        response = self.client.post(
            '/api/v2/forms/%s/submit_form/' % self.molo_form_page.id,
            post_data,
            format="json",
            content_type="application/json")

        self.assertEqual(response.status_code, 201)
        submissions = self.molo_form_page.get_submission_class().objects.all()
        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0].user.username, "some-uuid")
        self.assertEqual(User.objects.count(), 1)

    def test_submit_form_endpoint_with_uuid_saves_for_existing_user(self):
        User.objects.create(username="some-uuid")
        self.assertEqual(User.objects.count(), 1)

        data = {self.form_field_1.clean_name: "Tom",
                self.form_field_2.clean_name: "cat",
                self.form_field_3.clean_name: "Yellow"}
        post_data = {"uuid": "some-uuid"}
        post_data.update(data)

        response = self.client.post(
            '/api/v2/forms/%s/submit_form/' % self.molo_form_page.id,
            post_data,
            format="json",
            content_type="application/json")

        self.assertEqual(response.status_code, 201)
        submissions = self.molo_form_page.get_submission_class().objects.all()
        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0].user.username, "some-uuid")
        self.assertEqual(User.objects.count(), 1)

    def test_form_endpoint_raises_error_for_second_sub_if_not_allowed(self):
        user = User.objects.create(username="some-uuid")
        self.molo_form_page.get_submission_class().objects.create(
            user=user, form_data={}, page_id=self.molo_form_page.id
        )
        self.molo_form_page.allow_multiple_submissions_per_user = False
        self.molo_form_page.save()

        data = {self.form_field_1.clean_name: "Tom",
                self.form_field_2.clean_name: "cat",
                self.form_field_3.clean_name: "Yellow"}
        post_data = {"uuid": "some-uuid"}
        post_data.update(data)

        response = self.client.post(
            '/api/v2/forms/%s/submit_form/' % self.molo_form_page.id,
            post_data,
            format="json",
            content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "User has already submitted. Multiple submissions not allowed.",
            response.json()
        )
        submissions = self.molo_form_page.get_submission_class().objects.all()
        self.assertEqual(len(submissions), 1)
        form_data = json.loads(submissions[0].form_data)
        self.assertEqual(form_data, {})

    def test_submit_form_endpoint_returns_400_for_invalid_data(self):
        data = {self.form_field_1.clean_name: "Tom",
                self.form_field_2.clean_name: "cat",
                self.form_field_3.clean_name: "Copper"}

        response = self.client.post(
            '/api/v2/forms/%s/submit_form/' % self.molo_form_page.id,
            data,
            format="json",
            content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertIn('your_favourite_colour', response.json())
        submissions = self.molo_form_page.get_submission_class().objects.all()
        self.assertEqual(len(submissions), 0)

    def test_submit_form_endpoint_returns_400_for_unpublished_form(self):
        self.molo_form_page.live = False
        self.molo_form_page.save()
        data = {self.form_field_1.clean_name: "Tom",
                self.form_field_2.clean_name: "cat",
                self.form_field_3.clean_name: "Yellow"}

        response = self.client.post(
            '/api/v2/forms/%s/submit_form/' % self.molo_form_page.id,
            data,
            format="json",
            content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Submissions to unpublished forms are not allowed.",
            response.json()
        )
        submissions = self.molo_form_page.get_submission_class().objects.all()
        self.assertEqual(len(submissions), 0)

    def test_form_endpoint_returns_400_for_anon_sub_when_not_allowed(self):
        self.molo_form_page.allow_anonymous_submissions = False
        self.molo_form_page.save()

        data = {self.form_field_1.clean_name: "Tom",
                self.form_field_2.clean_name: "cat",
                self.form_field_3.clean_name: "Yellow"}

        response = self.client.post(
            '/api/v2/forms/%s/submit_form/' % self.molo_form_page.id,
            data,
            format="json",
            content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Anonymous submissions not allowed. Please send uuid.",
            response.json()
        )
        submissions = self.molo_form_page.get_submission_class().objects.all()
        self.assertEqual(len(submissions), 0)
