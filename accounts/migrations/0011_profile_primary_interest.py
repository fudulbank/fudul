# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-05 18:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_not_null_nickname'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='primary_interest',
            field=models.CharField(choices=[('SMLE', 'SMLE'), ('SNLE', 'SNLE'), ('RESIDENCY', 'Residency exams'), ('COLLEGE', 'Colege exams')], default='COLLEGE', max_length=20),
        ),
    ]
