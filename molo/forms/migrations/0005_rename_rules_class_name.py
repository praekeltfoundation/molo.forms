# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-07 19:57
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields
import molo.forms.blocks
import wagtail.core.blocks
import wagtail.core.fields


class Migration(migrations.Migration):

    dependencies = [
        ('wagtail_personalisation', '0018_segment_excluded_users'),
        ('forms', '0004_add_email_form'),
    ]

    operations = [
        migrations.CreateModel(
            name='FormCombinationRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', wagtail.core.fields.StreamField([('Rule', molo.forms.blocks.RuleSelectBlock()), ('Operator', wagtail.core.blocks.ChoiceBlock(choices=[('and', 'And'), ('or', 'Or')])), ('NestedLogic', wagtail.core.blocks.StructBlock([('rule_1', molo.forms.blocks.RuleSelectBlock(required=True)), ('operator', wagtail.core.blocks.ChoiceBlock(choices=[('and', 'And'), ('or', 'Or')])), ('rule_2', molo.forms.blocks.RuleSelectBlock(required=True))]))])),
                ('segment', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='forms_formcombinationrule_related', related_query_name='forms_formcombinationrules', to='wagtail_personalisation.Segment')),
            ],
            options={
                'verbose_name': 'Rule Combination',
            },
        ),
        migrations.CreateModel(
            name='FormGroupMembershipRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='forms.FormsSegmentUserGroup')),
                ('segment', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='forms_formgroupmembershiprule_related', related_query_name='forms_formgroupmembershiprules', to='wagtail_personalisation.Segment')),
            ],
            options={
                'verbose_name': 'Group membership rule',
            },
        ),
        migrations.RemoveField(
            model_name='combinationrule',
            name='segment',
        ),
        migrations.RemoveField(
            model_name='groupmembershiprule',
            name='group',
        ),
        migrations.RemoveField(
            model_name='groupmembershiprule',
            name='segment',
        ),
        migrations.DeleteModel(
            name='CombinationRule',
        ),
        migrations.DeleteModel(
            name='GroupMembershipRule',
        ),
    ]
