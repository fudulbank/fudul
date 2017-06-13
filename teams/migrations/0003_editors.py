# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-13 19:52
from __future__ import unicode_literals

from django.db import migrations

def add_editors(apps, schema_editor):
    Team = apps.get_model('teams', 'Team')
    Category = apps.get_model('exams', 'Category')
    editors = Team.objects.create(name="KSAU-HS COM Editors",
                                  code_name="ksauhs_com_editors",
                                  access='editors')
    category = Category.objects.get(slug='com',
                                    parent_category__slug="ksau-hs")
    editors.categories.add(category)

def remove_editors(apps, schema_editor):
    Team = apps.get_model('exams', 'Team')
    Team.objects.filter(code_name="ksauhs_com_editors").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0002_add_categories_and_exams'),
        ('teams', '0002_team_categories'),
    ]

    operations = [
        migrations.RunPython(add_editors,
                             reverse_code=remove_editors)
    ]
