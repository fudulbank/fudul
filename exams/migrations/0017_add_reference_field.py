# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-08-03 20:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0016_remove_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='revision',
            name='reference',
            field=models.TextField(blank=True, default=''),
        ),
    ]
