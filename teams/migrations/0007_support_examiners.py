# Generated by Django 2.2.5 on 2019-10-24 11:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0006_remove_team_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='is_examiner',
            field=models.BooleanField(default=False, verbose_name='This group represents a group of examiners'),
        ),
    ]
