# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-17 18:45
from __future__ import unicode_literals

from django.db import migrations

def fill_is_last(apps, schema_editor):
    Question = apps.get_model('exams', 'Question')
    for question in Question.objects.iterator():
        revision = question.revision_set.order_by("submission_date").last()
        revision.is_last = True
        revision.save()

def empty_is_last(apps, schema_editor):
    Revision = apps.get_model('exams', 'Revision')
    Revision.objects.update(is_last=False)


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0008_is_last'),
    ]

    operations = [
        migrations.RunPython(fill_is_last,
                             reverse_code=empty_is_last)
    ]
