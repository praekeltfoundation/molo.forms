# Generated by Django 3.1.5 on 2021-01-11 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forms', '0010_save_article_object'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='moloformsubmission',
            options={'verbose_name': 'form submission', 'verbose_name_plural': 'form submissions'},
        ),
        migrations.AddField(
            model_name='moloformfield',
            name='clean_name',
            field=models.CharField(blank=True, default='', help_text='Safe name of the form field, the label converted to ascii_snake_case', max_length=255, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='personalisableformfield',
            name='clean_name',
            field=models.CharField(blank=True, default='', help_text='Safe name of the form field, the label converted to ascii_snake_case', max_length=255, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='moloformpage',
            name='save_article_object',
            field=models.BooleanField(default=False, help_text='This will always save the related article as a hidden form field', verbose_name='Save Linked Article'),
        ),
        migrations.AlterField(
            model_name='personalisableformfield',
            name='field_type',
            field=models.CharField(choices=[('singleline', 'Single line text'), ('multiline', 'Multi-line text'), ('email', 'Email'), ('number', 'Number'), ('url', 'URL'), ('checkbox', 'Checkbox'), ('checkboxes', 'Checkboxes'), ('dropdown', 'Drop down'), ('radio', 'Radio buttons'), ('date', 'Date'), ('datetime', 'Date/time'), ('hidden', 'Hidden field')], max_length=16, verbose_name='field type'),
        ),
    ]
