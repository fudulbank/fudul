# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-12-22 12:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_add_name_display_prefrance'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='personal_email_confirmation_key',
            field=models.CharField(blank=True, max_length=40, verbose_name='unconfirmed email verification key'),
        ),
        migrations.AddField(
            model_name='profile',
            name='personal_email_confirmation_key_created',
            field=models.DateTimeField(blank=True, null=True, verbose_name='creation date of email confirmation key'),
        ),
        migrations.AddField(
            model_name='profile',
            name='personal_email_unconfirmed',
            field=models.EmailField(blank=True, help_text='Temporary email address when the user requests an email change.', max_length=254, verbose_name='unconfirmed email address'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='display_full_name',
            field=models.CharField(choices=[('Y', 'Display my full name'), ('N', 'Display only nickname')], default='N', max_length=1),
        ),
    ]