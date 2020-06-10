from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.template import Context
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware

from molo.core.models import Main, Languages, SiteLanguageRelation
from molo.core.tests.base import MoloTestCaseMixin
from molo.forms.models import (
    MoloFormPage, MoloFormField, ArticlePageForms,
    FormsIndexPage, PersonalisableForm, MoloFormSubmission)

from molo.forms.templatetags.molo_forms_tags import (
    get_form_list, url_to_anchor,
    load_user_choice_poll_form, forms_list_linked_to_pages)
from .base import create_form


def add_session_to_request(request):
    """Annotate a request object with a session"""
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()


class LoadUserChoicePollForm(TestCase, MoloTestCaseMixin):

    def setUp(self):
        self.mk_main()
        self.main = Main.objects.all().first()
        self.language_setting = Languages.objects.create(
            site_id=self.main.get_site().pk)
        self.english = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting,
            locale='en',
            is_active=True)
        self.forms_index = FormsIndexPage.objects.child_of(
            self.main).first()
        self.user = self.login()
        # create a requset object
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.request.site = self.site
        self.request.user = self.user
        add_session_to_request(self.request)

    def test_load_user_choice_poll_form(self):
        create_form([
            {
                "question": "I feel I can be myself around other people",
                "type": 'radio',
                "choices": ["agree", "disagree"],
                "required": True,
                "page_break": False,
            },
        ],
            language=self.english)
        form = MoloFormPage.objects.last()
        self.client.post(form.url, {
            'i-feel-i-can-be-myself-around-other-people':
                'agree',
            'ajax': 'True'
        })
        self.assertEqual(MoloFormSubmission.objects.count(), 1)
        self.assertTrue(load_user_choice_poll_form(
            {'request': self.request},
            form, 'i-feel-i-can-be-myself-around-other-people',
            'agree'))
        self.assertFalse(load_user_choice_poll_form(
            {'request': self.request},
            form, 'i-feel-i-can-be-myself-around-other-people',
            'disagree'))
        self.client.post(form.url, {
            'i-feel-i-can-be-myself-around-other-people':
                'disagree',
            'ajax': 'True'
        })
        self.assertEqual(MoloFormSubmission.objects.count(), 1)
        self.assertFalse(load_user_choice_poll_form(
            {'request': self.request},
            form, 'i-feel-i-can-be-myself-around-other-people',
            'agree'))
        self.assertTrue(load_user_choice_poll_form(
            {'request': self.request},
            form, 'i-feel-i-can-be-myself-around-other-people',
            'disagree'))


class FormListTest(TestCase, MoloTestCaseMixin):

    def create_molo_form_page(
            self,
            parent,
            title="Test Form",
            slug="test-form",
            **kwargs):
        molo_form_page = MoloFormPage(
            title=title,
            slug=slug,
            introduction='Introduction to Test Form ...',
            thank_you_text='Thank you for taking the Test Form',
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

    def create_personalisable_form(
            self,
            parent,
            title="Test Form",
            slug="test-form",
            **kwargs):
        personalisable_form = PersonalisableForm(
            title=title,
            slug=slug,
            introduction='Introduction to Test Form ...',
            thank_you_text='Thank you for taking the Test Form',
            **kwargs
        )

        parent.add_child(instance=personalisable_form)
        personalisable_form.save_revision().publish()
        form_field = MoloFormField.objects.create(
            page=personalisable_form,
            sort_order=1,
            label='Your favourite animal',
            field_type='singleline',
            required=True
        )
        return personalisable_form, form_field

    def setUp(self):
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
        self.forms_index = FormsIndexPage.objects.child_of(
            self.main).first()

        self.user = User.objects.create_user(
            'test', 'test@example.org', 'test')

        # create a requset object
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.request.site = self.site
        self.request.user = self.user
        add_session_to_request(self.request)
        self.user = self.login()

        # create direct questions
        self.direct_molo_form_page, direct_molo_form_field = (
            self.create_molo_form_page(
                parent=self.forms_index,
                title="direct form title",
                slug="direct_form_title",
                display_form_directly=True,
            ))
        self.client.post(reverse(
            'add_translation', args=[self.direct_molo_form_page.id, 'fr']))
        self.translated_direct_form = MoloFormPage.objects.get(
            slug='french-translation-of-direct-form-title')
        self.translated_direct_form.save_revision().publish()

        self.linked_molo_form_page, linked_molo_form_field = (
            self.create_molo_form_page(
                parent=self.forms_index,
                title="linked form title",
                slug="linked_form_title",
                display_form_directly=False,
                article_form_only=False,
            ))
        self.article_molo_form_page, article_molo_form_field = (
            self.create_molo_form_page(
                parent=self.forms_index,
                title="article form title(Reaction Question)",
                slug="article_form_title",
                display_form_directly=False,
                article_form_only=True,
            ))
        self.contact_form_page, linked_molo_form_field = (
            self.create_molo_form_page(
                parent=self.forms_index,
                title="test title",
                slug="test_tittle",
                contact_form=True,
            ))
        self.yourwords_molo_form_page, yourwords_molo_form_field = (
            self.create_molo_form_page(
                parent=self.forms_index,
                title="yourwords form title",
                slug="yourwords_form_title",
                your_words_competition=True,
            ))
        self.client.post(reverse(
            'add_translation', args=[self.linked_molo_form_page.id, 'fr']))
        self.translated_linked_form = MoloFormPage.objects.get(
            slug='french-translation-of-linked-form-title')
        self.translated_linked_form.save_revision().publish()

        self.personalisable_form, personalisable_form_field = (
            self.create_personalisable_form(
                parent=self.forms_index,
                title="personalisable form title",
                slug="personalisable_form_title",
            ))
        self.client.post(reverse(
            'add_translation', args=[self.personalisable_form.id, 'fr']))
        self.trans_personalisable_form = PersonalisableForm.objects.get(
            slug='french-translation-of-personalisable-form-title')
        self.trans_personalisable_form.save_revision().publish()

    def test_get_form_list_default(self):
        context = Context({
            'locale_code': 'en',
            'request': self.request,
        })
        context = get_form_list(context)
        self.assertEqual(len(context['forms']), 5)
        self.assertTrue(self.direct_molo_form_page in context['forms'])
        self.assertFalse(self.translated_linked_form in context['forms'])
        self.assertTrue(self.article_molo_form_page in context['forms'])
        self.assertTrue(self.linked_molo_form_page in context['forms'])
        self.assertTrue(self.yourwords_molo_form_page in context['forms'])
        self.assertTrue(self.contact_form_page in context['forms'])

        context = Context({
            'locale_code': 'fr',
            'request': self.request,
        })
        context = get_form_list(context)
        self.assertEqual(len(context['forms']), 5)
        self.assertFalse(self.direct_molo_form_page in context['forms'])
        self.assertTrue(self.translated_direct_form in context['forms'])
        self.assertTrue(self.yourwords_molo_form_page in context['forms'])
        self.assertTrue(self.article_molo_form_page in context['forms'])
        self.assertTrue(self.contact_form_page in context['forms'])

    def test_get_form_list_only_direct(self):
        context = Context({
            'locale_code': 'en',
            'request': self.request,
        })
        context = get_form_list(context, only_direct_forms=True)
        self.assertEqual(len(context['forms']), 1)
        self.assertTrue(self.direct_molo_form_page in context['forms'])
        self.assertTrue(self.linked_molo_form_page not in context['forms'])
        context = Context({
            'locale_code': 'fr',
            'request': self.request,
        })
        context = get_form_list(context, only_direct_forms=True)
        self.assertEqual(len(context['forms']), 1)
        self.assertTrue(self.translated_direct_form in context['forms'])
        self.assertTrue(
            self.translated_linked_form not in context['forms'])

    def test_get_form_list_only_yourwords(self):
        context = Context({
            'locale_code': 'en',
            'request': self.request,
        })
        context = get_form_list(context, only_yourwords=True)
        self.assertEqual(len(context['forms']), 1)
        self.assertTrue(self.yourwords_molo_form_page in context['forms'])
        self.assertTrue(self.linked_molo_form_page not in context['forms'])

    def test_get_form_list_only_contact_forms(self):
        context = Context({
            'locale_code': 'en',
            'request': self.request,
        })
        context = get_form_list(context, contact_form=True)
        self.assertEqual(len(context['forms']), 1)
        self.assertTrue(self.contact_form_page in context['forms'])
        self.assertTrue(self.linked_molo_form_page not in context['forms'])
        self.assertTrue(self.yourwords_molo_form_page not in context['forms'])

    def test_get_form_list_only_linked(self):
        context = Context({
            'locale_code': 'en',
            'request': self.request,
        })
        context = get_form_list(context, only_linked_forms=True)
        self.assertEqual(len(context['forms']), 1)
        self.assertTrue(self.direct_molo_form_page not in context['forms'])
        self.assertTrue(self.linked_molo_form_page in context['forms'])
        context = Context({
            'locale_code': 'fr',
            'request': self.request,
        })
        context = get_form_list(context, only_linked_forms=True)
        self.assertEqual(len(context['forms']), 1)
        self.assertTrue(
            self.translated_direct_form not in context['forms'])
        self.assertTrue(self.translated_linked_form in context['forms'])

    def test_forms_list_linked_to_pages(self):
        context = Context({
            'locale_code': 'en',
            'request': self.request,
        })
        survey = self.direct_molo_form_page
        article = self.mk_article(self.main)
        article_page_form = ArticlePageForms(form=survey, page=article)
        article.forms.add(article_page_form)
        res = forms_list_linked_to_pages(context, article)
        self.assertEqual(res['forms'][0]['molo_form_page'], survey)

    def test_get_form_list_arg_error(self):
        context = Context({
            'locale_code': 'en',
            'request': self.request,
        })
        with self.assertRaises(ValueError):
            context = get_form_list(
                context, only_linked_forms=True, only_direct_forms=True,)

    def test_get_form_list_personalisable_form(self):
        context = Context({
            'locale_code': 'en',
            'request': self.request,
        })
        context = get_form_list(context, personalisable_form=True)
        self.assertEqual(len(context['forms']), 1)
        self.assertTrue(
            self.direct_molo_form_page not in context['forms'])
        self.assertTrue(self.personalisable_form in context['forms'])
        context = Context({
            'locale_code': 'fr',
            'request': self.request,
        })
        context = get_form_list(context, personalisable_form=True)
        self.assertEqual(len(context['forms']), 1)
        self.assertTrue(
            self.translated_direct_form not in context['forms'])
        self.assertTrue(
            self.trans_personalisable_form in context['forms'])


class TestUrlToAnchorTemplateFilter(TestCase):

    def test_url_to_anchor(self):
        link = 'http://abc.com?somerandomvar=123'
        self.assertEqual(
            '<a href="{0}">{0}</a>'.format(link),
            url_to_anchor(link)
        )
