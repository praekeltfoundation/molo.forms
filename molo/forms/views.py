from __future__ import unicode_literals

import json

from django.http import Http404
from django.urls import reverse
from django.conf.urls import url
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.models import Group
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView, View, FormView

from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from wagtail.admin import messages
from wagtail.core.models import Page
from wagtail.utils.pagination import paginate
from wagtail.core.utils import cautious_slugify
from wagtail.admin.utils import permission_required

from wagtail.contrib.forms.forms import FormBuilder
from wagtail.api.v2.endpoints import PagesAPIEndpoint
from wagtail.contrib.forms.utils import get_forms_for_user

from wagtail_personalisation.forms import SegmentAdminForm
from wagtail_personalisation.models import Segment

from molo.core.models import ArticlePage
from molo.core.templatetags.core_tags import get_pages

from .serializers import MoloFormSerializer
from .forms import CSVGroupCreationForm, ReactionQuestionChoiceForm
from .models import (
    MoloFormPage, FormsIndexPage, PersonalisableForm,
    ReactionQuestionResponse, ReactionQuestionChoice,
    ReactionQuestion,
)


def index(request):
    form_pages = get_forms_for_user(request.user)
    form_pages = (
        form_pages.descendant_of(request.site.root_page).specific()
    )
    paginator, form_pages = paginate(request, form_pages)

    return render(request, 'wagtailforms/index.html', {
        'form_pages': form_pages,
        'page_obj': form_pages,
    })


class SegmentCountForm(SegmentAdminForm):
    class Meta:
        model = Segment
        fields = ['type', 'status', 'count', 'name', 'match_any']


def get_segment_user_count(request):
    f = SegmentCountForm(request.POST)
    context = {}
    if f.is_valid():
        rules = [
            form.instance for formset in f.formsets.values()
            for form in formset
            if form not in formset.deleted_forms
        ]
        count = f.count_matching_users(rules, f.instance.match_any)
        context = {'segmentusercount': count}
    else:
        errors = f.errors
        # Get the errors for the Rules forms
        for formset in f.formsets.values():
            if formset.has_changed():
                for form in formset:
                    if form.errors:
                        id_prefix = form.prefix
                        for name, error in form.errors.items():
                            input_name = id_prefix + "-%s" % name
                            errors[input_name] = error

        context = {'errors': errors}

    return JsonResponse(context)


class ResultsPercentagesJson(View):
    def get(self, *args, **kwargs):
        pages = self.request.site.root_page.get_descendants()
        ids = []
        for page in pages:
            ids.append(page.id)
        form = get_object_or_404(
            MoloFormPage, slug=kwargs['slug'], id__in=ids)
        # Get information about form fields
        data_fields = [
            (field.clean_name, field.label)
            for field in form.get_form_fields()
        ]

        results = dict()
        # Get all submissions for current page
        submissions = (
            form.get_submission_class().objects.filter(page=form))
        for submission in submissions:
            data = submission.get_data()

            # Count results for each question
            for name, label in data_fields:
                answer = data.get(name)
                if answer is None:
                    # Something wrong with data.
                    # Probably you have changed questions
                    # and now we are receiving answers for old questions.
                    # Just skip them.
                    continue

                if type(answer) is list:
                    # answer is a list if the field type is 'Checkboxes'
                    answer = u', '.join(answer)

                question_stats = results.get(label, {})
                question_stats[cautious_slugify(answer)] = \
                    question_stats.get(cautious_slugify(answer), 0) + 1
                results[label] = question_stats

        for question, answers in results.items():
            total = sum(answers.values())
            for key in answers.keys():
                answers[key] = int(round((answers[key] * 100) / total))
        return JsonResponse(results)


class FormSuccess(TemplateView):
    template_name = "forms/molo_form_page_success.html"

    def get_context_data(self, *args, **kwargs):
        context = super(TemplateView, self).get_context_data(*args, **kwargs)
        pages = self.request.site.root_page.get_descendants()
        ids = []
        for page in pages:
            ids.append(page.id)
        form = get_object_or_404(
            MoloFormPage, slug=kwargs['slug'], id__in=ids)
        results = dict()
        if form.show_results:
            # Get information about form fields
            data_fields = [
                (field.clean_name, field.label)
                for field in form.get_form_fields()
            ]

            # Get all submissions for current page
            submissions = (
                form.get_submission_class().objects.filter(page=form))
            for submission in submissions:
                data = submission.get_data()

                # Count results for each question
                for name, label in data_fields:
                    answer = data.get(name)
                    if answer is None:
                        # Something wrong with data.
                        # Probably you have changed questions
                        # and now we are receiving answers for old questions.
                        # Just skip them.
                        continue

                    if type(answer) is list:
                        # answer is a list if the field type is 'Checkboxes'
                        answer = u', '.join(answer)

                    question_stats = results.get(label, {})
                    question_stats[answer] = question_stats.get(answer, 0) + 1
                    results[label] = question_stats
        if form.show_results_as_percentage:
            for question, answers in results.items():
                total = sum(answers.values())
                for key in answers.keys():
                    answers[key] = int((answers[key] * 100) / total)
        context.update({'self': form, 'results': results})
        return context


def submission_article(request, form_id, submission_id):
    # get the specific submission entry
    form_page = get_object_or_404(Page, id=form_id).specific
    SubmissionClass = form_page.get_submission_class()

    submission = SubmissionClass.objects.filter(
        page=form_page).filter(pk=submission_id).first()
    if not submission.article_page:
        form_index_page = (
            FormsIndexPage.objects.descendant_of(
                request.site.root_page).live().first())
        body = []
        for value in submission.get_data().values():
            body.append({"type": "paragraph", "value": str(value)})
        article = ArticlePage(
            title='yourwords-entry-%s' % cautious_slugify(submission_id),
            slug='yourwords-entry-%s' % cautious_slugify(submission_id),
            body=json.dumps(body)
        )
        form_index_page.add_child(instance=article)
        article.save_revision()
        article.unpublish()

        submission.article_page = article
        submission.save()
        return redirect('/admin/pages/%d/move/' % article.id)
    return redirect('/admin/pages/%d/edit/' % submission.article_page.id)


# CSV creation views
@permission_required('auth.add_group')
def create(request):
    group = Group()
    if request.method == 'POST':
        form = CSVGroupCreationForm(
            request.POST, request.FILES, instance=group)
        if form.is_valid():
            form.save()

            messages.success(
                request,
                _("Group '{0}' created. "
                  "Imported {1} user(s).").format(
                    group, group.user_set.count()),
                buttons=[
                    messages.button(reverse('wagtailusers_groups:edit',
                                            args=(group.id,)), _('Edit'))
                ]
            )
            return redirect('wagtailusers_groups:index')

        messages.error(request, _(
            "The group could not be created due to errors."))
    else:
        form = CSVGroupCreationForm(instance=group)

    return render(request, 'csv_group_creation/create.html', {
        'form': form
    })


class MoloFormsEndpoint(PagesAPIEndpoint):
    base_serializer_class = MoloFormSerializer

    listing_default_fields = \
        PagesAPIEndpoint.listing_default_fields + ['homepage_introduction']

    def get_queryset(self):
        '''
        This is overwritten in order to only show Forms
        '''
        queryset = MoloFormPage.objects.public()
        # exclude PersonalisableForms and ones that require login
        queryset = queryset.exclude(
            id__in=PersonalisableForm.objects.public())
        request = self.request

        # Filter by site
        queryset = queryset.descendant_of(
            request.site.root_page, inclusive=True)

        return queryset

    def submit_form(self, request, pk):
        # Get the form
        instance = self.get_object()
        if not instance.live:
            raise ValidationError(
                detail=_("Submissions to unpublished forms are not allowed."))
        builder = FormBuilder(instance.form_fields.all())

        # Populate the form with the submitted data
        form_class = builder.get_form_class()
        form = form_class(request.data)
        form.user = request.user

        # Validate and create the submission
        if form.is_valid():
            instance.process_form_submission(form)
            return Response(form.cleaned_data, status=status.HTTP_201_CREATED)
        else:
            raise ValidationError(detail=form.errors)

    @classmethod
    def get_urlpatterns(cls):
        # Overwritten to also return the submit_form url
        patterns = super(MoloFormsEndpoint, cls).get_urlpatterns()
        patterns = patterns + [
            url(
                r'^(?P<pk>\d+)/submit_form/$',
                cls.as_view({'post': 'submit_form'}),
                name='submit'
            ),
        ]
        return patterns


class ReactionQuestionChoiceFeedbackView(TemplateView):
    template_name = 'forms/reaction_question_feedback.html'

    def get_context_data(self, **kwargs):
        context = super(ReactionQuestionChoiceFeedbackView,
                        self).get_context_data(**kwargs)
        locale = self.request.LANGUAGE_CODE
        choice_slug = self.kwargs.get('choice_slug')
        context['request'] = self.request
        main_lang_choice = ReactionQuestionChoice.objects.descendant_of(
            self.request.site.root_page).filter(
            slug=choice_slug)
        choice = get_pages(context, main_lang_choice, locale)
        if choice:
            choice = choice[0]
        else:
            choice = main_lang_choice
        context.update({'choice': choice})
        article_slug = self.kwargs.get('article_slug')
        article = ArticlePage.objects.descendant_of(
            self.request.site.root_page).filter(slug=article_slug).first()
        context.update({'article': article})
        return context


class ReactionQuestionChoiceView(FormView):
    form_class = ReactionQuestionChoiceForm
    template_name = 'forms/reaction_question.html'

    def get_success_url(self, *args, **kwargs):
        article_slug = self.kwargs.get('article_slug')
        article = ArticlePage.objects.descendant_of(
            self.request.site.root_page).filter(slug=article_slug).first()
        if not article:
            raise Http404
        choice_id = self.get_context_data()['form'].data.get('choice')
        choice = get_object_or_404(ReactionQuestionChoice, pk=choice_id)
        question_id = self.kwargs.get('question_id')
        return reverse('molo.forms:reaction-feedback', kwargs={
            'question_id': question_id, 'article_slug': article.slug,
            'choice_slug': choice.slug})

    def get_context_data(self, *args, **kwargs):
        context = super(
            ReactionQuestionChoiceView, self).get_context_data(*args, **kwargs)
        question_id = self.kwargs.get('question_id')
        question = get_object_or_404(ReactionQuestion, pk=question_id)
        context.update({'question': question})
        return context

    def form_valid(self, form, *args, **kwargs):
        question_id = self.kwargs.get('question_id')
        question = get_object_or_404(ReactionQuestion, pk=question_id)
        question = question.get_main_language_page().specific
        choice_pk = form.cleaned_data['choice']
        choice = get_object_or_404(ReactionQuestionChoice, pk=choice_pk)
        article_slug = self.kwargs.get('article_slug')
        # get main language article and store the vote there
        article = ArticlePage.objects.descendant_of(
            self.request.site.root_page).filter(slug=article_slug).first()
        if hasattr(article, 'get_main_language_page'):
            article = article.get_main_language_page()
        if not article:
            raise Http404
        if not question.has_user_submitted_reaction_response(
                self.request, question_id, article.pk):
            created = ReactionQuestionResponse.objects.create(
                question=question,
                article=article)
            if created:
                created.choice = choice
                created.save()
                created.set_response_as_submitted_for_session(
                    self.request, article)
            if self.request.user.is_authenticated:
                created.user = self.request.user
                created.save()

        else:
            if 'ajax' in self.request.POST and \
                    self.request.POST['ajax'] == 'True':
                response = ReactionQuestionResponse.objects.filter(
                    article=article.pk, question=question_id,
                    user=self.request.user).last()
                response.choice = choice
                response.save()
            else:
                messages.error(
                    self.request,
                    "You have already given feedback on this article.")
        return super(ReactionQuestionChoiceView, self).form_valid(
            form, *args, **kwargs)
