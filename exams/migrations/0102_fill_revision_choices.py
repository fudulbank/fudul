# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-05-26 19:33
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import Count, Prefetch

# The purpose of merging choices is:
#
# 1) When a new revision is created, we want the answers and
#    corrections created in relation to to previous revisions' choices
#    to be accessible.
# 2) To reduce the duplication overhead on Fudul's database.

def forward(apps, schema_editor):
    Question = apps.get_model('exams', 'Question')
    Revision = apps.get_model('exams', 'Revision')
    Choice = apps.get_model('exams', 'Choice')
    Answer = apps.get_model('exams', 'Answer')
    Highlight = apps.get_model('exams', 'Highlight')

    for revision in Revision.objects.filter(choices__isnull=True)\
                                    .prefetch_related(Prefetch('choice_set', to_attr='choice_list'))\
                                    .order_by('pk'):
       print(f"Filling revision.choices for revision #{revision.pk}...")
       revision.choices.add(*revision.choice_list)

    for choice in Choice.objects.select_related('revision', 'revision__question')\
                                .filter(revision__isnull=False)\
                                .order_by('pk'):
        print(f"Filling choice.question for choice #{choice.pk}...")
        choice.question = choice.revision.question
        choice.save()

    total_obsolete_count = 0
    current_question_count = 0
    question_pool = Question.objects.annotate(revision_count=Count('revision'))\
                                    .filter(revision_count__gte=2)\
                                    .order_by('pk')
    total_question_count = question_pool.count()

    for question in question_pool:
        choices_scanned = []
        for choice in Choice.objects.select_related('answer_correction')\
                                    .filter(revision__question=question):
            choice_identifier = (choice.text, choice.is_right) 
            if choice_identifier in choices_scanned:
                continue
            else:
                choices_scanned.append(choice_identifier)

            similar_choices = Choice.objects.filter(revision__question=question,
                                                    text=choice.text,
                                                    is_right=choice.is_right)\
                                            .select_related('revision')

            if similar_choices.count() == 1:
                continue

            # We will pick the preferred choice depending on the
            # AnswerCorrection related to it.
            correction_count = similar_choices.filter(answer_correction__isnull=False)\
                                              .count()
            if correction_count >= 2:
                # Pick the one with the most likes
                preferred_choice = similar_choices.annotate(likes=Count('answer_correction__supporting_users'))\
                                                  .order_by('-likes')\
                                                  .first()
            elif correction_count == 1:
                # Pick the one with a correction.
                preferred_choice = similar_choices.filter(answer_correction__isnull=False).first()
            elif correction_count == 0:
                # Pick the first one
                preferred_choice = similar_choices.order_by('pk').first()

            # Mergeing includes: revisions, answers and highlights.
            obsolete_choices = similar_choices.exclude(pk=preferred_choice.pk)
            obsolete_count = obsolete_choices.count()
            total_obsolete_count += obsolete_count
            percentage = round(current_question_count / total_question_count * 100, 1)

            print("Question {} ({}%): We are removing {} obsolete choices...".format(question.pk, percentage,obsolete_count))
            for obsolete_choice in obsolete_choices:
                # 1) Revisions
                print(f"Adding choice \"{preferred_choice.text}\" (#{preferred_choice.pk}) to revision #{obsolete_choice.revision.pk} in place of choice #{obsolete_choice.pk}")
                revision = obsolete_choice.revision
                revision.choices.add(preferred_choice)
                revision.choices.remove(obsolete_choice)
                # 2) Answers
                Answer.objects.filter(choice=obsolete_choice).update(choice=preferred_choice)
                # 3) Highlights
                for highlight in Highlight.objects.filter(stricken_choices=obsolete_choice):
                    highlight.stricken_choices.remove(obsolete_choice)
                    highlight.stricken_choices.add(preferred_choice)

        current_question_count += 1

    print("We obsoleted {} choices in total.".format(total_obsolete_count))

class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0101_revision_choices'),
    ]

    operations = [
        migrations.RunPython(forward)
    ]
