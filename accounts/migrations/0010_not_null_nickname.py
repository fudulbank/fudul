# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-01-09 01:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_nickname_not_required'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='nickname',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
    ]
