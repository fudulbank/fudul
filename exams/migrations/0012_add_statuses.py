# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-22 06:57
from __future__ import unicode_literals

from django.db import migrations

status_choices = (
    ('COMPLETE','Complete and valid question'),
    ('WRITING_ERROR', 'Writing errors'),
    ('INCOMPLETE_ANSWERS', 'Incomplete answers'),
    ('INCOMPLETE_QUESTION', 'Incomplete question'),
    ('UNSOLVED', 'Unsolved question'),
)

def add_statuses(apps, schema_editor):
    Status = apps.get_model('exams', 'Status')
    Question = apps.get_model('exams', 'Question')

    for code_name, human_name in status_choices:
        status = Status.objects.create(name=human_name, code_name=code_name)
        status.question_set.add(*Question.objects.filter(status=code_name))

def remove_statuses(apps, schema_editor):
    Status = apps.get_model('exams', 'Status')
    Question = apps.get_model('exams', 'Question')

    for code_name, human_name in status_choices:
        status = Status.objects.get(code_name=code_name)
        Question.objects.filter(statuses=status).update(status=code_name)

class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0011_status_model'),
    ]

    operations = [
        migrations.RunPython(add_statuses,
                             reverse_code=remove_statuses)
    ]