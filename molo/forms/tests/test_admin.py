import json

from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.client import Client

from molo.core.models import SiteLanguageRelation, Main, Languages, ArticlePage
from molo.core.tests.base import MoloTestCaseMixin
from molo.forms.models import (
    MoloFormPage,
    MoloFormField,
    FormsIndexPage,
    PersonalisableForm,
    PersonalisableFormField,
)
from molo.forms.rules import FormSubmissionDataRule
from ..forms import CHARACTER_COUNT_CHOICE_LIMIT
from wagtail_personalisation.models import Segment
from wagtail_personalisation.rules import UserIsLoggedInRule

from .base import create_molo_form_page

User = get_user_model()


class TestFormAdminViews(TestCase, MoloTestCaseMixin):
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
        self.super_user = User.objects.create_superuser(
            username='testuser', password='password', email='test@email.com')

    def create_molo_form_page(self, parent, **kwargs):
        molo_form_page = MoloFormPage(
            title='Test Form', slug='test-form',
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
            admin_label='fav_animal',
            field_type='singleline',
            required=True
        )
        return molo_form_page, molo_form_field

    def create_personalisable_molo_form_page(self, parent, **kwargs):
        # create segment for personalisation
        test_segment = Segment.objects.create(name="Test Segment")
        UserIsLoggedInRule.objects.create(
            segment=test_segment,
            is_logged_in=True)

        personalisable_form = PersonalisableForm(
            title='Test Form', slug='test-form',
            introduction='Introduction to Test Form ...',
            thank_you_text='Thank you for taking the Test Form',
            **kwargs
        )

        parent.add_child(instance=personalisable_form)
        personalisable_form.save_revision().publish()

        molo_form_field = PersonalisableFormField.objects.create(
            field_type='singleline',
            label='Question 1',
            admin_label='question_1',
            page=personalisable_form,
            segment=test_segment)

        return personalisable_form, molo_form_field

    def test_form_create_invalid_with_duplicate_questions(self):
        self.client.force_login(self.super_user)
        response = self.client.get(
            '/admin/pages/add/forms/moloformpage/%d/' %
            self.forms_index.pk)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        data = form.initial
        data.update(
            form.formsets['form_fields'].management_form.initial)
        data.update({u'description-count': 0})
        data.update({
            'form_fields-0-admin_label': 'a',
            'form_fields-0-label': 'question 1',
            'form_fields-0-default_value': 'a',
            'form_fields-0-field_type': 'radio',
            'form_fields-0-help_text': 'b',
            'form_fields-1-admin_label': 'b',
            'form_fields-1-label': 'question 1',
            'form_fields-1-default_value': 'a',
            'form_fields-1-field_type': 'radio',
            'form_fields-1-help_text': 'b',
            'go_live_at': '',
            'expire_at': '',
            'image': '',
            'form_fields-0-ORDER': 1,
            'form_fields-0-required': 'on',
            'form_fields-0-skip_logic-0-deleted': '',
            'form_fields-0-skip_logic-0-id': 'None',
            'form_fields-0-skip_logic-0-order': 0,
            'form_fields-0-skip_logic-0-type': 'skip_logic',
            'form_fields-0-skip_logic-0-value-choice': 'a',
            'form_fields-0-skip_logic-0-value-question_0': 'a',
            'form_fields-0-skip_logic-0-value-skip_logic': 'next',
            'form_fields-0-skip_logic-0-value-form': '',
            'form_fields-0-skip_logic-count': 1,
            'form_fields-1-ORDER': 2,
            'form_fields-1-required': 'on',
            'form_fields-1-skip_logic-0-deleted': '',
            'form_fields-1-skip_logic-0-id': 'None',
            'form_fields-1-skip_logic-0-order': 0,
            'form_fields-1-skip_logic-0-type': 'skip_logic',
            'form_fields-1-skip_logic-0-value-choice': 'a',
            'form_fields-1-skip_logic-0-value-question_0': 'a',
            'form_fields-1-skip_logic-0-value-skip_logic': 'next',
            'form_fields-1-skip_logic-0-value-form': '',
            'form_fields-1-skip_logic-count': 1,
            'form_fields-INITIAL_FORMS': 0,
            'form_fields-MAX_NUM_FORMS': 1000,
            'form_fields-MIN_NUM_FORMS': 0,
            'form_fields-TOTAL_FORMS': 2,
            'terms_and_conditions-INITIAL_FORMS': 0,
            'terms_and_conditions-MAX_NUM_FORMS': 1000,
            'terms_and_conditions-MIN_NUM_FORMS': 0,
            'terms_and_conditions-TOTAL_FORMS': 0,
        })
        response = self.client.post(
            '/admin/pages/add/forms/moloformpage/%d/' %
            self.forms_index.pk, data=data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form'].formsets['form_fields']
        err = u'This question appears elsewhere in the form. ' \
              u'Please rephrase one of the questions.'
        self.assertTrue(err in form.errors[1]['label'])

    def test_form_edit_view(self):
        self.client.force_login(self.super_user)
        child_of_index_page = create_molo_form_page(
            self.forms_index,
            title="Child of FormsIndexPage Form",
            slug="child-of-formsindexpage-form"
        )
        form_field = MoloFormField.objects.create(
            page=child_of_index_page, field_type='radio', choices='a,b,c')
        response = self.client.get(
            '/admin/pages/%d/edit/' % child_of_index_page.pk)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        data = form.initial
        data.update(
            form.formsets['form_fields'].management_form.initial)
        data.update({u'description-count': 0})
        data.update({
            'form_fields-0-admin_label': 'a',
            'form_fields-0-label': 'a',
            'form_fields-0-default_value': 'a',
            'form_fields-0-field_type': form_field.field_type,
            'form_fields-0-help_text': 'a',
            'form_fields-0-id': form_field.pk,
            'go_live_at': '',
            'expire_at': '',
            'image': '',
            'form_fields-0-ORDER': 1,
            'form_fields-0-required': 'on',
            'form_fields-0-skip_logic-0-deleted': '',
            'form_fields-0-skip_logic-0-id': 'None',
            'form_fields-0-skip_logic-0-order': 0,
            'form_fields-0-skip_logic-0-type': 'skip_logic',
            'form_fields-0-skip_logic-0-value-choice': 'a',
            'form_fields-0-skip_logic-0-value-question_0': 'a',
            'form_fields-0-skip_logic-0-value-skip_logic': 'next',
            'form_fields-0-skip_logic-0-value-form': '',
            'form_fields-0-skip_logic-count': 1,
            'form_fields-INITIAL_FORMS': 1,
            'form_fields-MAX_NUM_FORMS': 1000,
            'form_fields-MIN_NUM_FORMS': 0,
            'form_fields-TOTAL_FORMS': 1,
            'terms_and_conditions-INITIAL_FORMS': 0,
            'terms_and_conditions-MAX_NUM_FORMS': 1000,
            'terms_and_conditions-MIN_NUM_FORMS': 0,
            'terms_and_conditions-TOTAL_FORMS': 0,
        })
        response = self.client.post(
            '/admin/pages/%d/edit/' % child_of_index_page.pk, data=data)
        self.assertEqual(
            response.context['message'],
            u"Page 'Child of FormsIndexPage Form' has been updated."
        )
        data.update({
            'form_fields-0-skip_logic-0-value-choice':
                'a' + 'a' * CHARACTER_COUNT_CHOICE_LIMIT,
        })
        response = self.client.post(
            '/admin/pages/%d/edit/' % child_of_index_page.pk, data=data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form'].formsets['form_fields']
        err = u'The combined choices\' maximum characters ' \
              u'limit has been exceeded ({max_limit} ' \
              u'character(s)).'
        self.assertTrue(
            err.format(max_limit=CHARACTER_COUNT_CHOICE_LIMIT) in
            form.errors[0]['field_type'].error_list[0]
        )

        data.update({
            'form_fields-0-field_type': 'checkbox',
        })
        response = self.client.post(
            '/admin/pages/%d/edit/' % child_of_index_page.pk, data=data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form'].formsets['form_fields']
        self.assertTrue(
            'Checkbox must include only 2 Answer Options.' in
            form.errors[0]['field_type'][0]
        )

    def test_form_edit_invalid_with_duplicate_questions(self):
        self.client.force_login(self.super_user)
        child_of_index_page = create_molo_form_page(
            self.forms_index,
            title="Child of FormsIndexPage Form",
            slug="child-of-formsindexpage-form"
        )
        form_field_1 = MoloFormField.objects.create(
            page=child_of_index_page, label='question 1', field_type='radio',
            choices='a,b,c')
        form_field_2 = MoloFormField.objects.create(
            page=child_of_index_page, label='question 2', field_type='radio',
            choices='a,b,c')
        response = self.client.get(
            '/admin/pages/%d/edit/' % child_of_index_page.pk)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        data = form.initial
        data.update(
            form.formsets['form_fields'].management_form.initial)
        data.update({u'description-count': 0})
        data.update({
            'form_fields-0-admin_label': 'a',
            'form_fields-0-label': form_field_1.label,
            'form_fields-0-default_value': 'a',
            'form_fields-0-field_type': form_field_1.field_type,
            'form_fields-0-help_text': 'a',
            'form_fields-0-id': form_field_1.pk,
            'form_fields-1-admin_label': 'a',
            'form_fields-1-label': form_field_1.label,
            'form_fields-1-default_value': 'a',
            'form_fields-1-field_type': form_field_2.field_type,
            'form_fields-1-help_text': 'a',
            'form_fields-1-id': form_field_2.pk,
            'go_live_at': '',
            'expire_at': '',
            'image': '',
            'form_fields-0-ORDER': 1,
            'form_fields-0-required': 'on',
            'form_fields-0-skip_logic-0-deleted': '',
            'form_fields-0-skip_logic-0-id': 'None',
            'form_fields-0-skip_logic-0-order': 0,
            'form_fields-0-skip_logic-0-type': 'skip_logic',
            'form_fields-0-skip_logic-0-value-choice': 'a',
            'form_fields-0-skip_logic-0-value-question_0': 'a',
            'form_fields-0-skip_logic-0-value-skip_logic': 'next',
            'form_fields-0-skip_logic-0-value-form': '',
            'form_fields-0-skip_logic-count': 1,
            'form_fields-1-ORDER': 2,
            'form_fields-1-required': 'on',
            'form_fields-1-skip_logic-0-deleted': '',
            'form_fields-1-skip_logic-0-id': 'None',
            'form_fields-1-skip_logic-0-order': 0,
            'form_fields-1-skip_logic-0-type': 'skip_logic',
            'form_fields-1-skip_logic-0-value-choice': 'a',
            'form_fields-1-skip_logic-0-value-question_0': 'a',
            'form_fields-1-skip_logic-0-value-skip_logic': 'next',
            'form_fields-1-skip_logic-0-value-form': '',
            'form_fields-1-skip_logic-count': 1,
            'form_fields-INITIAL_FORMS': 2,
            'form_fields-MAX_NUM_FORMS': 1000,
            'form_fields-MIN_NUM_FORMS': 0,
            'form_fields-TOTAL_FORMS': 2,
            'terms_and_conditions-INITIAL_FORMS': 0,
            'terms_and_conditions-MAX_NUM_FORMS': 1000,
            'terms_and_conditions-MIN_NUM_FORMS': 0,
            'terms_and_conditions-TOTAL_FORMS': 0,
        })
        response = self.client.post(
            '/admin/pages/%d/edit/' % child_of_index_page.pk, data=data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form'].formsets['form_fields']
        err = u'This question appears elsewhere in the form. ' \
              u'Please rephrase one of the questions.'
        self.assertTrue(err in form.errors[1]['label'])

    def test_convert_to_article(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page(parent=self.section_index)

        self.client.login(username='tester', password='tester')
        response = self.client.get(molo_form_page.url)
        self.assertContains(response, molo_form_page.title)
        self.assertContains(response, molo_form_page.introduction)
        self.assertContains(response, molo_form_field.label)
        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): 'python'
        }, follow=True)
        self.client.logout()
        self.client.login(
            username='testuser',
            password='password'
        )

        # test shows convert to article button when no article created yet
        response = self.client.get(
            '/admin/forms/submissions/%s/' % molo_form_page.id)

        self.assertContains(response, 'Convert to Article')

        # convert submission to article
        SubmissionClass = molo_form_page.get_submission_class()

        submission = SubmissionClass.objects.filter(
            page=molo_form_page).first()
        response = self.client.get(
            '/forms/submissions/%s/article/%s/' % (
                molo_form_page.id, submission.pk))
        self.assertEqual(response.status_code, 302)
        article = ArticlePage.objects.last()
        submission = SubmissionClass.objects.filter(
            page=molo_form_page).first()
        self.assertEqual(article.title, article.slug)
        self.assertEqual(submission.article_page, article)

        self.assertEqual(
            sorted([
                body_elem['type'] for body_elem in article.body.stream_data]
            ),
            ['paragraph', 'paragraph', 'paragraph'],
        )

        self.assertEqual(
            sorted([
                body_elem['value'] for body_elem in article.body.stream_data]
            ),
            [str(submission.submit_time), 'python', 'tester'],
        )

        # first time it goes to the move page
        self.assertEqual(
            response['Location'],
            '/admin/pages/%d/move/' % article.id)

        # second time it should redirect to the edit page
        response = self.client.get(
            '/forms/submissions/%s/article/%s/' % (
                molo_form_page.id, submission.pk))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            '/admin/pages/%d/edit/' % article.id)
        response = self.client.get(
            '/admin/forms/submissions/%s/' % molo_form_page.id)

        # it should not show convert to article as there is already article
        self.assertNotContains(response, 'Convert to Article')

    def test_export_submission_standard_form(self):
        molo_form_page, molo_form_field = \
            self.create_molo_form_page(parent=self.section_index)

        self.client.force_login(self.user)
        answer = 'PYTHON'
        response = self.client.post(molo_form_page.url, {
            molo_form_field.label.lower().replace(' ', '-'): answer
        })

        self.client.force_login(self.super_user)
        response = self.client.get(
            '/admin/forms/submissions/%s/' % (molo_form_page.id),
            {'action': 'CSV'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username')
        self.assertContains(response, 'Submission Date')
        self.assertNotContains(response, molo_form_field.label)
        self.assertContains(response, molo_form_field.admin_label)
        self.assertContains(response, answer)

    def test_export_submission_personalisable_form(self):
        molo_form_page, molo_form_field = (
            self.create_personalisable_molo_form_page(
                parent=self.section_index))

        answer = 'PYTHON'

        molo_form_page.get_submission_class().objects.create(
            form_data=json.dumps({"question-1": answer},
                                 cls=DjangoJSONEncoder),
            page=molo_form_page,
            user=self.user
        )

        self.client.force_login(self.super_user)
        response = self.client.get(
            '/admin/forms/submissions/{}/'.format(molo_form_page.id),
            {'action': 'CSV'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username')
        self.assertContains(response, 'Submission Date')
        self.assertNotContains(response, molo_form_field.label)

        self.assertContains(
            response,
            '{} ({})'.format(molo_form_field.admin_label,
                             molo_form_field.segment.name))

        self.assertContains(response, self.user.username)
        self.assertContains(response, answer)

    def test_form_index_view_displays_all_forms(self):
        child_of_index_page = create_molo_form_page(
            self.forms_index,
            title="Child of FormsIndexPage Form",
            slug="child-of-formsindexpage-form"
        )

        child_of_article_page = create_molo_form_page(
            self.article,
            title="Child of Article Form",
            slug="child-of-article-form"
        )

        self.client.force_login(self.super_user)
        response = self.client.get('/admin/forms/')
        self.assertContains(response, child_of_index_page.title)
        self.assertContains(response, child_of_article_page.title)

    def test_segment_submission_rule_edit_shows_field_label(self):
        # create form page
        molo_form_page, molo_form_field = (
            self.create_personalisable_molo_form_page(
                parent=self.section_index))
        # create segment and rule
        test_segment = Segment.objects.create(name="Test Segment")
        rule = FormSubmissionDataRule(
            segment=test_segment,
            form=molo_form_page, operator=FormSubmissionDataRule.EQUALS,
            expected_response='super random text',
            field_name='question-1')
        rule.save()
        test_segment.save()

        self.client.force_login(self.super_user)
        response = self.client.get(
            '/admin/wagtail_personalisation/segment/edit/%d/' %
            test_segment.pk)

        self.assertNotContains(response, rule.field_name)
        self.assertContains(response, molo_form_field.label)

    def test_form_edit_view_invalid_formfields(self):
        self.client.force_login(self.super_user)
        child_of_index_page = create_molo_form_page(
            self.forms_index,
            title="Child of FormsIndexPage Form",
            slug="child-of-formsindexpage-form"
        )
        form_field = MoloFormField.objects.create(
            page=child_of_index_page, field_type='radio', choices='a,b,c')
        response = self.client.get(
            '/admin/pages/%d/edit/' % child_of_index_page.pk)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        data = form.initial
        data.update(
            form.formsets['form_fields'].management_form.initial)
        data.update({u'description-count': 0})
        data.update({
            'form_fields-0-admin_label': '',
            'form_fields-0-label': '',
            'form_fields-0-default_value': '',
            'form_fields-0-field_type': form_field.field_type,
            'form_fields-0-help_text': '',
            'form_fields-0-id': form_field.pk,
            'go_live_at': '',
            'expire_at': '',
            'image': '',
            'form_fields-0-ORDER': 1,
            'form_fields-0-required': 'on',
            'form_fields-0-skip_logic-0-deleted': '',
            'form_fields-0-skip_logic-0-id': 'None',
            'form_fields-0-skip_logic-0-order': 0,
            'form_fields-0-skip_logic-0-type': 'skip_logic',
            'form_fields-0-skip_logic-0-value-choice': 'a',
            'form_fields-0-skip_logic-0-value-question_0': 'a',
            'form_fields-0-skip_logic-0-value-skip_logic': 'next',
            'form_fields-0-skip_logic-0-value-form': '',
            'form_fields-0-skip_logic-count': 1,
            'form_fields-INITIAL_FORMS': 1,
            'form_fields-MAX_NUM_FORMS': 1000,
            'form_fields-MIN_NUM_FORMS': 0,
            'form_fields-TOTAL_FORMS': 1,
            'terms_and_conditions-INITIAL_FORMS': 0,
            'terms_and_conditions-MAX_NUM_FORMS': 1000,
            'terms_and_conditions-MIN_NUM_FORMS': 0,
            'terms_and_conditions-TOTAL_FORMS': 0,
        })
        response = self.client.post(
            '/admin/pages/%d/edit/' % child_of_index_page.pk, data=data)
        self.assertEqual(
            response.context['message'],
            u"The page could not be saved due to validation errors"
        )
