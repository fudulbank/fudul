# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-20 19:51
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0053_creare_explanations'),
    ]

    operations = [
        migrations.RenameField(
            model_name='explanationrevision',
            old_name='figure',
            new_name='explanation_figure',
        ),
        migrations.RenameField(
            model_name='explanationrevision',
            old_name='text',
            new_name='explanation_text',
        ),
    ]
