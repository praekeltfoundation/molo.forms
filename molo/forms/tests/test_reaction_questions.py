# coding=utf-8
from django.urls import reverse
from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from django.contrib.messages import get_messages
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType

from molo.core.models import (
    Main,
    Languages,
    SiteSettings,
    ArticleOrderingChoices,
    SiteLanguageRelation,)


from molo.forms.templatetags.molo_forms_tags import (
    load_reaction_choice_submission_count,
    load_user_choice_reaction_question,
)

from molo.forms.models import (
    ReactionQuestion,
    ReactionQuestionChoice,
    ReactionQuestionResponse,
    ReactionQuestionIndexPage
)
from molo.forms.tests.base import FormsTestCase


class TestReactionQuestionResultsAdminView(FormsTestCase, TestCase):
    def setUp(self):
        self.mk_main()
        self.english = SiteLanguageRelation.objects.create(
            language_setting=Languages.for_site(self.main.get_site()),
            locale='en',
            is_active=True)

        self.french = SiteLanguageRelation.objects.create(
            language_setting=Languages.for_site(self.main.get_site()),
            locale='fr',
            is_active=True)

        self.assertTrue(self.section_index)
        self.yourmind = self.mk_section(
            self.section_index, title='Your mind')
        self.yourmind_fr = self.mk_section_translation(
            self.yourmind, self.french, title='Your mind in french')

        self.mk_main2()
        self.main2 = Main.objects.all().last()
        self.language_setting2 = Languages.objects.create(
            site_id=self.main2.get_site().pk)

        self.english2 = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting2,
            locale='en', is_active=True)

        self.spanish = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting2,
            locale='es', is_active=True)

        self.yourmind2 = self.mk_section(
            self.section_index2, title='Your mind2')

        self.reaction_index = self.get_reaction_index(self.main)
        self.reaction_index2 = self.get_reaction_index(self.main2)

    def test_reaction_question_appears_in_wagtail_admin(self):
        User.objects.create_superuser(
            username='testuser', password='password', email='test@email.com')
        self.client.login(username='testuser', password='password')
        article = self.mk_article(self.yourmind)
        article_site_2 = self.mk_article(self.yourmind2)
        question = self.mk_reaction_question(self.reaction_index, article)
        question2 = self.mk_reaction_question(
            self.reaction_index2, article_site_2)
        response = self.client.get(
            '/admin/forms/reactionquestion/'
        )

        self.assertContains(
            response,
            '<a href="/admin/reactionquestion/%s/results/">'
            'Test Question</a>' % question.pk)
        self.assertNotContains(
            response,
            '<a href="/admin/reactionquestion/%s/results/">'
            'Test Question</a>' % question2.pk)

    def test_article_appears_in_wagtail_admin_summary(self):
        User.objects.create_superuser(
            username='testuser', password='password', email='test@email.com')
        self.client.login(username='testuser', password='password')
        article = self.mk_article(self.yourmind)
        article_site_2 = self.mk_article(self.yourmind2)
        self.mk_reaction_question(self.reaction_index, article)
        self.mk_reaction_question(
            self.reaction_index2, article_site_2)
        response = self.client.get(
            '/admin/core/articlepage/'
        )

        self.assertContains(
            response,
            '<a href="/admin/reactionquestion/%s/results/summary/">'
            'Test page 0</a>' % article.pk)
        self.assertNotContains(
            response,
            '<a href="/admin/reactionquestion/%s/results/summary/">'
            'Test page 0</a>' % article_site_2.pk)

    def test_reaction_question_results_view(self):
        super_user = User.objects.create_superuser(
            username='testuser', password='password', email='test@email.com')
        self.client.login(username='testuser', password='password')

        article = self.mk_article(self.yourmind)
        question = self.mk_reaction_question(self.reaction_index, article)
        choice1 = question.get_children().first()
        response = self.client.post(reverse(
            'molo.forms:reaction-vote', kwargs={
                'question_id': question.id, 'article_slug': article.slug}),
            {'choice': choice1.id})

        response = self.client.get(
            '/admin/reactionquestion/{0}/results/'.format(question.id)
        )

        expected_headings_html = '<tr><th>Submission Date</th><th>Answer</th>'\
                                 '<th>User</th><th>Article</th></tr>'

        self.assertContains(response, expected_headings_html, html=True)
        self.assertContains(response, choice1.title)
        self.assertContains(response, super_user.username)
        self.assertContains(response, article.title)

        # test CSV download
        response = self.client.get(
            '/admin/reactionquestion/{0}/results/?action=download'.format(
                question.id)
        )
        created_date = ReactionQuestionResponse.objects.first().created_at

        expected_output = (
            'Submission Date,Answer,User,Article\r\n'
            '{0},yes,{1},{2}\r\n'
        ).format(
            created_date,
            super_user.username, article.title
        )
        self.assertContains(response, expected_output)

    def test_reaction_question_results_summary_view(self):
        User.objects.create_superuser(
            username='testuser', password='password', email='test@email.com')
        self.client.login(username='testuser', password='password')

        article = self.mk_article(self.yourmind)
        question = self.mk_reaction_question(self.reaction_index, article)
        choice1 = question.get_children().first()
        response = self.client.post(reverse(
            'molo.forms:reaction-vote', kwargs={
                'question_id': question.id, 'article_slug': article.slug}),
            {'choice': choice1.id})

        response = self.client.get(
            '/admin/reactionquestion/{0}/results/summary/'.format(article.id)
        )

        expected_headings_html = '<tr><th>Article</th><th>yes</th>'\
                                 '<th>maybe</th><th>no</th></tr>'
        self.assertContains(response, expected_headings_html, html=True)
        self.assertContains(response, 'Test page 0')

        # test CSV download
        response = self.client.get(
            '/admin/reactionquestion/{0}/'
            'results/summary/?action=download'.format(article.id)
        )

        expected_output = (
            'Article,yes,maybe,no\r\n'
            '{0},1,0,0\r\n'
        ).format(
            article.title,
        )
        self.assertContains(response, expected_output)


class TestReactionQuestions(FormsTestCase, TestCase):

    def setUp(self):
        self.mk_main()
        self.english = SiteLanguageRelation.objects.create(
            language_setting=Languages.for_site(self.main.get_site()),
            locale='en',
            is_active=True)

        self.french = SiteLanguageRelation.objects.create(
            language_setting=Languages.for_site(self.main.get_site()),
            locale='fr',
            is_active=True)

        self.yourmind = self.mk_section(
            self.section_index, title='Your mind')

        self.yourmind_fr = self.mk_section_translation(
            self.yourmind, self.french, title='Your mind in french')

        self.mk_main2()
        self.language_setting2 = Languages.objects.create(
            site_id=self.main2.get_site().pk)
        self.english2 = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting2,
            locale='en',
            is_active=True)

        self.spanish = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting2,
            locale='es',
            is_active=True)

        self.yourmind2 = self.mk_section(
            self.section_index2, title='Your mind2')

        self.reaction_index = self.get_reaction_index(self.main)
        self.reaction_index2 = self.get_reaction_index(self.main2)

    def test_can_react_on_article_with_and_without_ajax_call(self):
        article = self.mk_article(self.yourmind)
        article.save_revision().publish()
        question = self.mk_reaction_question(self.reaction_index, article)
        self.user = self.login()

        site = 'http://{}:{}'.format(self.site.hostname, self.site.port)
        response = self.client.get(article.url.replace(site, ''))

        self.assertContains(response, question.title)

        for choice in question.get_children():
            self.assertContains(response, choice.title)

        choice1 = question.get_children().first()
        choice2 = question.get_children().last()
        self.assertEqual(ReactionQuestionResponse.objects.all().count(), 0)

        kw = {'question_id': question.id, 'article_slug': article.slug}
        data = {'choice': choice1.id}
        response = self.client.post(
            reverse('molo.forms:reaction-vote', kwargs=kw), data=data)

        self.assertEqual(ReactionQuestionResponse.objects.all().count(), 1)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'], '/reaction/test-page-0/20/yes/feedback/')

        response = self.client.get('/reaction/test-page-0/20/yes/feedback/')

        self.assertContains(
            response, '<a href="/sections-main-1/your-mind/test-page-0/">')

        self.assertContains(response, 'well done')

        # test user can only submit once
        response = self.client.post(
            reverse('molo.forms:reaction-vote', kwargs=kw),
            data=data)
        self.assertEqual(ReactionQuestionResponse.objects.all().count(), 1)
        self.assertEqual(
            ReactionQuestionResponse.objects.last().choice.pk, choice1.pk)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        # this should show if the submit is not done via ajax
        self.assertEqual(
            str(messages[0]),
            'You have already given feedback on this article.')

        # submit with ajax in post data
        response = self.client.post(
            reverse('molo.forms:reaction-vote', kwargs=kw),
            {'choice': choice2.id, 'ajax': 'True'})

        # there should still only be one response object from user
        # but the vote should change from choice 1 to choice 2
        self.assertEqual(ReactionQuestionResponse.objects.all().count(), 1)
        self.assertEqual(
            ReactionQuestionResponse.objects.last().choice.pk, choice2.pk)
        messages = list(get_messages(response.wsgi_request))
        # no error message if the submit is done via ajax
        self.assertEqual(len(messages), 0)

    def test_correct_reaction_shown_for_locale(self):
        article = self.mk_article(self.yourmind)
        question = self.mk_reaction_question(self.reaction_index, article)
        self.mk_article_translation(
            article, self.french,
            title=article.title + ' in french',)

        translated_question = self.mk_reaction_translation(
            question, article, self.french,
            title=question.title + ' in french',)

        translated_choice = ReactionQuestionChoice(
            title='ja', success_message='mooi gedoen')

        question.add_child(instance=translated_choice)
        translated_choice.save_revision().publish()
        translated_choice = self.mk_translation(
            question.get_first_child(), self.french, translated_choice)

        self.client.get('/locale/fr/')

        response = self.client.get(
            '/sections-main-1/your-mind/test-page-0-in-french/')

        self.assertContains(response, 'Test Question in french')

        self.client.post(reverse(
            'molo.forms:reaction-vote', kwargs={
                'question_id': translated_question.id,
                'article_slug': article.slug}),
            {'choice': translated_choice.id})
        self.assertEqual(ReactionQuestionResponse.objects.all().count(), 1)

        response = self.client.get('/reaction/test-page-0/20/yes/feedback/')
        self.assertContains(
            response, '<a href="/sections-main-1/your-mind/test-page-0/">')
        self.assertContains(response, 'mooi gedoen')


class TestAdminPermission(FormsTestCase, TestCase):

    def setUp(self):
        self.mk_main()
        self.language_setting = Languages.objects.create(
            site_id=self.main.get_site().pk)
        self.english = SiteLanguageRelation.objects.create(
            language_setting=self.language_setting,
            locale='en',
            is_active=True)
        self.assertTrue(self.section_index)
        # create content types
        wagtailadmin_content_type, created = ContentType.objects.get_or_create(
            app_label='wagtailadmin',
            model='admin'
        )
        reaction_question_content_type = ContentType.objects.get_for_model(
            ReactionQuestionResponse)
        # Create Wagtail admin permission
        access_admin, created = Permission.objects.get_or_create(
            content_type=wagtailadmin_content_type,
            codename='access_admin',
            name='Can access Wagtail admin'
        )
        # Create reaction question view response
        self.reaction_question = Permission.objects.get(
            content_type=reaction_question_content_type,
            codename='can_view_response')
        # create a group
        self.test_group, _ = Group.objects.get_or_create(name='Test group')
        self.test_group.permissions.add(access_admin)
        # create a user and add the user to the group
        user = User.objects.create_user(
            username='username',
            password='password',
            email='login@email.com',
            is_staff=True,
        )
        user.groups.add(self.test_group)

        self.reaction_index = self.get_reaction_index(self.main)

    def test_superuser_can_see_reaction_question_modeladmin(self):
        User.objects.create_superuser(
            username='super', password='password', email='login@email.com')
        self.client.login(username='super', password='password')

        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reactionquestion')

    def test_user_has_perm_can_see_reaction_question_modeladmin(self):
        self.client.login(username='username', password='password')
        user = User.objects.filter(username='username').first()

        # User shoudn't see the reaction question model admin
        self.assertTrue(user.has_perm('wagtailadmin.access_admin'))
        self.assertFalse(user.has_perm('forms.can_view_response'))

        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'reactionquestion')

        # User shoud see the reaction question model admin
        self.test_group.permissions.add(self.reaction_question)
        user = User.objects.filter(username='username').first()
        self.assertIn(self.test_group, user.groups.all())

        self.assertTrue(user.has_perm('wagtailadmin.access_admin'))
        self.assertTrue(user.has_perm('forms.can_view_response'))

        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reactionquestion')


class TestReactionQuestionChoiceFeedbackView(FormsTestCase, TestCase):
    """Test response reaction """

    def setUp(self):
        self.mk_main()
        self.english = SiteLanguageRelation.objects.create(
            language_setting=Languages.for_site(self.main.get_site()),
            locale='en',
            is_active=True)

        self.assertTrue(self.section_index)
        self.yourmind = self.mk_section(
            self.section_index, title='Your mind')
        self.reaction_index = self.get_reaction_index(self.main)

    def test_view(self):
        article = self.mk_article(self.yourmind)
        question = self.mk_reaction_question(self.reaction_index, article)
        choice = ReactionQuestionChoice(title='yes', success_message='Yes!!!')
        question.add_child(instance=choice)
        choice.save_revision().publish()

        choice2 = ReactionQuestionChoice(title='no', success_message='No!!!')
        question.add_child(instance=choice2)
        choice2.save_revision().publish()

        kw = {
            'article_slug': article.slug,
            'question_id': question.pk,
            'choice_slug': choice.slug,
        }
        url = reverse('molo.forms:reaction-feedback', kwargs=kw)

        res = self.client.get(url)
        self.assertTrue(res.status_code, 200)
        self.assertEqual(
            res.template_name,
            ['patterns/basics/articles/reaction_question_feedback.html'])
        self.assertContains(res, article.title)
        self.assertContains(res, choice.success_message)

    def test_load_user_choice_reaction_question(self):
        article = self.mk_articles(self.yourmind, 1)[0]
        question = ReactionQuestion(title='q1')
        ReactionQuestionIndexPage.objects.last().add_child(instance=question)
        question.save_revision().publish()

        choice = ReactionQuestionChoice(title='yes')
        question.add_child(instance=choice)
        choice.save_revision().publish()

        choice2 = ReactionQuestionChoice(title='no')
        question.add_child(instance=choice2)
        choice2.save_revision().publish()

        user = User.objects.create_superuser(
            username='testuser', password='password', email='test@email.com')

        ReactionQuestionResponse.objects.create(
            choice=choice, article=article, question=question,
            user=user)
        request = RequestFactory().get('/')
        request.user = user

        self.assertTrue(load_user_choice_reaction_question(
            {'request': request},
            question=question,
            choice=choice,
            article=article)
        )

        self.assertFalse(load_user_choice_reaction_question(
            {'request': request},
            question=question,
            choice=choice2,
            article=article)
        )

    def test_reaction_question_submission_count(self):
        article = self.mk_articles(self.yourmind, 1)[0]
        question = ReactionQuestion(title='q1')
        ReactionQuestionIndexPage.objects.last().add_child(instance=question)
        question.save_revision().publish()

        choice = ReactionQuestionChoice(title='yes')
        question.add_child(instance=choice)
        choice.save_revision().publish()

        choice2 = ReactionQuestionChoice(title='no')
        question.add_child(instance=choice2)
        choice2.save_revision().publish()

        ReactionQuestionResponse.objects.create(
            choice=choice, article=article, question=question)

        count = load_reaction_choice_submission_count(
            choice=choice, article=article, question=question)
        self.assertEqual(count, 1)

        count = load_reaction_choice_submission_count(
            choice=choice2, article=article, question=question)
        self.assertEqual(count, 0)

