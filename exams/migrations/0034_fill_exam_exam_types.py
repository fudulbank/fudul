# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-25 21:48
from __future__ import unicode_literals

from django.db import migrations

def add_exam_types(apps, schema_editor):
    Exam = apps.get_model('exams', 'Exam')
    ExamType = apps.get_model('exams', 'ExamType')
    Category = apps.get_model('exams', 'Category')

    for exam in Exam.objects.all():
        exam_types = ExamType.objects.none()
        category = exam.category
        while category:
            exam_types |= category.exam_types.all()
            category = category.parent_category
        exam.exam_types = exam_types

def remove_exam_types(apps, schema_editor):
    Exam = apps.get_model('exams', 'Exam')

    for exam in Exam.objects.filter(exam_types__isnull=False):
        exam.exam_types.clear()

class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0033_exam_exam_types'),
    ]

    operations = [
        migrations.RunPython(add_exam_types,
                             reverse_code=remove_exam_types)
    ]
