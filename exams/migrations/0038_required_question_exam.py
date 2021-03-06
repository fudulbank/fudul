# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-26 06:53
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0037_fill_exam'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='exam',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='exams.Exam'),
        ),
        migrations.AlterField(
            model_name='question',
            name='subjects',
            field=models.ManyToManyField(blank=True, to='exams.Subject'),
        ),
    ]
