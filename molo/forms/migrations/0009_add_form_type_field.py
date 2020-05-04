# Generated by Django 2.2.12 on 2020-05-04 14:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forms', '0008_articlepageforms'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='moloformpage',
            name='contact_form',
        ),
        migrations.RemoveField(
            model_name='moloformpage',
            name='your_words_competition',
        ),
        migrations.AddField(
            model_name='moloformpage',
            name='form_type',
            field=models.IntegerField(choices=[(1, 'form'), (2, 'contact'), (3, 'competition'), (4, 'reaction')], default=1, help_text='How will this form be used?'),
        ),
    ]
