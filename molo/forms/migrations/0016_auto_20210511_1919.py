# Generated by Django 3.1.10 on 2021-05-11 19:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('forms', '0015_auto_20210511_1919'),
    ]

    operations = [
        migrations.RenameField(
            model_name='moloformsubmission',
            old_name='is_winnder',
            new_name='is_winner',
        ),
    ]
