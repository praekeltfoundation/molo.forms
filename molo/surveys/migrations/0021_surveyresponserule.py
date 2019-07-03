# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-11-22 15:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0020_formfield_admin_label'),
        ('wagtail_personalisation', '0015_static_users')
    ]

    operations = [
        migrations.CreateModel(
            name='SurveyResponseRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('segment', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='surveys_surveyresponserule_related', related_query_name='%(app_label)s_%(class)ss', to='wagtail_personalisation.Segment')),
                ('survey', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='surveys.MoloSurveyPage', verbose_name='survey')),
            ],
            options={
                'verbose_name': 'Survey response rule',
            },
        ),
    ]
