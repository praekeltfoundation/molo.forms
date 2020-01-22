# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def create_forms_index(apps, schema_editor):
    from molo.core.models import Main
    from molo.forms.models import (
        FormsIndexPage, FormsTermsAndConditionsIndexPage
    )
    mains = Main.objects.all()

    for main in mains:
        forms_index = FormsIndexPage(title='Forms', slug='molo-forms')
        main.add_child(instance=forms_index)
        forms_index.save_revision().publish()

        terms_index = FormsTermsAndConditionsIndexPage(
            title='Terms and Conditions', slug='terms-conditions-indexpage')
        forms_index.add_child(instance=terms_index)
        terms_index.save_revision().publish()

        reactionquestion_index = FormsIndexPage(
            title='Reaction Questions', slug='reaction-questions-indexpage')
        forms_index.add_child(instance=reactionquestion_index)
        reactionquestion_index.save_revision().publish()

        contactforms_index = FormsIndexPage(
            title='Contact Forms', slug='contact-forms-indexpage')
        forms_index.add_child(instance=contactforms_index)
        contactforms_index.save_revision().publish()

        yourwords_index = FormsIndexPage(
            title='Your Words', slug='yourwords-indexpage')
        forms_index.add_child(instance=yourwords_index)
        yourwords_index.save_revision().publish()

        polls_index = FormsIndexPage(title='Polls', slug='polls-indexpage')
        forms_index.add_child(instance=polls_index)
        polls_index.save_revision().publish()

        surveys_index = FormsIndexPage(
            title='Surveys', slug='surveys-indexpage')
        forms_index.add_child(instance=surveys_index)
        surveys_index.save_revision().publish()


class Migration(migrations.Migration):

    dependencies = [
        ('forms', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_forms_index),
    ]
