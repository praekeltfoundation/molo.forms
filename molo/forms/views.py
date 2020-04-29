from __future__ import unicode_literals

import json
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from wagtail.core.models import Page

from django.conf.urls import url
from django.views.generic import TemplateView, View
from molo.forms.models import MoloFormPage, FormsIndexPage, PersonalisableForm
from molo.core.models import ArticlePage
from django.shortcuts import get_object_or_404, redirect

from wagtail.core.utils import cautious_slugify

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.translation import ugettext as _
from wagtail.utils.pagination import paginate

from wagtail.admin import messages
from wagtail.admin.utils import permission_required
from wagtail_personalisation.forms import SegmentAdminForm
from wagtail_personalisation.models import Segment

from wagtail.contrib.forms.forms import FormBuilder
from wagtail.contrib.forms.utils import get_forms_for_user

from .forms import CSVGroupCreationForm
from wagtail.api.v2.endpoints import PagesAPIEndpoint
from .serializers import MoloFormSerializer


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

        # Get the user or create a new one
        UserModel = get_user_model()
        uuid = request.data.get("uuid", None)
        user = None
        if uuid:
            user = UserModel.objects.get_or_create(username=uuid)[0]
            request.user = user

        if not user and not instance.allow_anonymous_submissions:
            raise ValidationError(
                detail="Anonymous submissions not allowed. Please send uuid."
            )

        if user and not instance.allow_multiple_submissions_per_user:
            if instance.has_user_submitted_form(request, instance.id):
                raise ValidationError(
                    detail="User has already submitted. "
                    "Multiple submissions not allowed."
                )

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
