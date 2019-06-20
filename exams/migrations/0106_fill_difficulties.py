# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-06-20 18:52
from __future__ import unicode_literals

from django.db import migrations

def forward(apps, schema_editor):
    Difficulty = apps.get_model('exams', 'Difficulty')
    Answer = apps.get_model('exams', 'Answer')

    Difficulty.objects.create(label="Easy: Questions you should not miss",
                              tooltip='These are the questions answered correctly by 75% or more of examinees.',
                              upper_limit=100,
                              lower_limit=76)
    Difficulty.objects.create(label='Doable: Questions you can manage',
                              tooltip='These are the questions answered correctly by 51-75% of examinees.',
                              upper_limit=75,
                              lower_limit=51)
    Difficulty.objects.create(label='Tricky: Questions to pay attention to',
                              tooltip='These are the questions answered correctly by 26-50% of examinees.',
                              upper_limit=50,
                              lower_limit=26)
    Difficulty.objects.create(label='Challenging: Questions that can get you in trouble',
                              tooltip='These are the questions answered correctly only by 25% or less of examinees.',
                              upper_limit=25,
                              lower_limit=0)        

    for answer in Answer.objects.select_related('session'):
        similar_answers = Answer.objects.filter(question_id=answer.question_id,
                                                session__submitter_id=answer.session.submitter_id)\
                                        .order_by('pk')
        first_answer = similar_answers.first()
        if not first_answer.is_first:
            first_answer.is_first = True
            answer.save()

def backward(apps, schema_editor):
    Difficulty = apps.get_model('exams', 'Difficulty')
    Answer = apps.get_model('exams', 'Answer')
    Difficulty.objects.all().delete()
    Answer.objects.update(is_first=False)

class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0105_difficulty'),
    ]

    operations = [
        migrations.RunPython(forward, backward)
    ]
