import re

from django import template
from django.forms.fields import MultipleChoiceField

from copy import copy
from wagtail.core.models import Page
from molo.forms.models import (
    MoloFormPage, FormsIndexPage, PersonalisableForm)

from molo.core.templatetags.core_tags import get_pages
from django.shortcuts import get_object_or_404

register = template.Library()


def get_form_list(
        context,
        only_linked_forms=False,
        only_direct_forms=False,
        only_yourwords=False,
        personalisable_form=False,
        contact_form=False,
):
    if only_linked_forms and only_direct_forms:
        raise ValueError('arguments "only_linked_forms" and '
                         '"only_direct_forms" cannot both be True')

    context = copy(context)
    locale_code = context.get('locale_code')
    main = context['request']._wagtail_site.root_page
    page = FormsIndexPage.objects.child_of(main).live().first()
    if page:
        forms = []
        if only_linked_forms:
            forms = (MoloFormPage.objects.descendant_of(page).filter(
                language__is_main_language=True, display_form_directly=False,
                contact_form=False, article_form_only=False,
                your_words_competition=False
            ).exact_type(MoloFormPage).specific())
        elif only_direct_forms:
            forms = (MoloFormPage.objects.descendant_of(page).filter(
                language__is_main_language=True, display_form_directly=True,
                article_form_only=False, your_words_competition=False,
            ).exact_type(MoloFormPage).specific())
        elif only_yourwords:
            forms = (MoloFormPage.objects.descendant_of(page).filter(
                language__is_main_language=True,
                your_words_competition=True,
            ).exact_type(MoloFormPage).specific())
        elif personalisable_form:
            forms = (PersonalisableForm.objects.descendant_of(page).filter(
                language__is_main_language=True,
            ).exact_type(PersonalisableForm).specific())

        elif contact_form:
            forms = (MoloFormPage.objects.descendant_of(page).filter(
                language__is_main_language=True,
                contact_form=True).exact_type(
                MoloFormPage).specific())

        else:
            forms = (MoloFormPage.objects.descendant_of(page).filter(
                language__is_main_language=True,
            ).exact_type(MoloFormPage).specific())
    else:
        forms = MoloFormPage.objects.none()
    context.update({
        'forms': get_pages(context, forms, locale_code)
    })
    return context


def add_form_objects_to_forms(context):
    forms = []
    for form_page in context['forms']:
        form = None
        if isinstance(form_page, MoloFormPage):
            if (form_page.allow_multiple_submissions_per_user or
                    not form_page.has_user_submitted_form(
                        context['request'], form_page.id)):
                form = form_page.get_form()

            forms.append({
                'molo_form_page': form_page,
                'form': form,
            })

    context.update({
        'forms': forms,
    })

    return context


@register.inclusion_tag('forms/forms_headline.html', takes_context=True)
def forms_list_headline(context):
    return get_form_list(context)


@register.inclusion_tag('forms/forms_list.html', takes_context=True)
def forms_list(
        context, pk=None, only_linked_forms=False,
        only_direct_forms=False, only_yourwords=False,
        personalisable_form=False, contact_form=False):

    context = get_form_list(
        context,
        only_linked_forms=only_linked_forms,
        only_direct_forms=only_direct_forms,
        only_yourwords=only_yourwords,
        personalisable_form=personalisable_form,
        contact_form=contact_form,
    )
    return add_form_objects_to_forms(context)


@register.simple_tag(takes_context=True)
def load_user_choice_poll_form(context, form, field, choice):
    if not form or not field:
        return False
    request = context['request']
    form = form.specific.get_main_language_page()
    SubmissionClass = form.specific.get_submission_class()
    submissions = SubmissionClass.objects.filter(
        page=form, user=request.user)
    if not submissions.exists():
        return False
    for submission in submissions:
        data = submission.get_data()
        if field in data and data[field] == choice:
            return True
    return False


@register.simple_tag(takes_context=True)
def submission_has_article(context, form_id, submission_id):
    form_page = get_object_or_404(Page, id=form_id).specific
    SubmissionClass = form_page.get_submission_class()
    submission = SubmissionClass.objects.filter(
        page=form_page).filter(pk=submission_id).first()
    if submission.article_page is None:
        return False
    return True


@register.inclusion_tag('forms/forms_list.html', takes_context=True)
def forms_list_for_pages(context, pk=None, page=None):
    context = copy(context)
    locale_code = context.get('locale_code')
    if page:
        forms = (
            MoloFormPage.objects.descendant_of(page).filter(
                language__is_main_language=True).specific())
    else:
        forms = MoloFormPage.objects.none()

    context.update({
        'forms': get_pages(context, forms, locale_code)
    })
    return add_form_objects_to_forms(context)


@register.inclusion_tag('forms/forms_list.html', takes_context=True)
def forms_list_linked_to_pages(context, article):
    _context = copy(context)
    locale_code = _context.get('locale_code')

    queryset = article.forms.all()\
        .values_list('form', flat=True)
    forms = MoloFormPage.objects\
        .filter(pk__in=queryset)

    forms = get_pages(_context, forms, locale_code)
    _context['forms'] = forms
    return add_form_objects_to_forms(context)


@register.filter(name='is_multiple_choice_field')
def is_multiple_choice_field(value):
    return isinstance(value.field, MultipleChoiceField)


@register.filter(name='url_to_anchor')
def url_to_anchor(value):
    def find_links(text):
        url_pattern = 'http[s]?://' \
                      '(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]' \
                      '|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        url = re.findall(url_pattern, text)
        return url
    links = find_links(value)
    for link in links:
        value = value.replace(link, '<a href="{0}">{0}</a>'.format(link))
    return value
