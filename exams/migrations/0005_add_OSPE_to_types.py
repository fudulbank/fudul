# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-16 06:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0004_add_status_choices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='exam_type',
            field=models.CharField(choices=[('FINAL', 'Final'), ('MIDTERM', 'Midterm'), ('OSPE', 'OSPE')], max_length=15),
        ),
        migrations.AlterField(
            model_name='question',
            name='status',
            field=models.CharField(choices=[('COMPLETE', 'Complete and valid question'), ('WRITING_ERROR', 'Writing errors'), ('INCOMPLETE_ANSWERS', 'Incomplete answers'), ('INCOMPLETE_QUESTION', 'Incomplete question'), ('UNSOLVED', 'Unsolved question')], max_length=30),
        ),
    ]
