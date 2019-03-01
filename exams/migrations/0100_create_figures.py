# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2019-03-01 16:16
from __future__ import unicode_literals

from django.db import migrations
from django.conf import settings
from hashlib import sha256
import itertools
import os

BUF_SIZE = 65536

def get_hexdigest(media_path):
    try:
        f = open(media_path, 'rb')
    except FileNotFoundError:
        return

    file_hash = sha256()
    while True:
        data = f.read(BUF_SIZE)
        if not data:
            break
        file_hash.update(data)
    file_hexdigest = file_hash.hexdigest()
    return file_hexdigest

def forward(apps, schema_editor):
    Figure = apps.get_model('exams', 'Figure')
    Revision = apps.get_model('exams', 'Revision')
    ExplanationRevision = apps.get_model('exams',
                                         'ExplanationRevision')

    # In our way to fill Figure, we will abandon duplicated files
    MEDIA_DIRS = ['revision_images', 'explanation_images']
    hashes = {}
    for directory in MEDIA_DIRS:
        directory_path = os.path.join(settings.MEDIA_ROOT, directory)
        try:
            files = os.listdir(directory_path)
        except FileNotFoundError:
            continue
        for filename in files:
            file_full_path = os.path.join(directory_path, filename)
            file_hexdigest = get_hexdigest(file_full_path)
            if file_hexdigest and not file_hexdigest in hashes:
                hashes[file_hexdigest] = file_full_path

    revisions_with_figures = itertools.chain(Revision.objects.exclude(figure=""),
                                             ExplanationRevision.objects.exclude(explanation_figure=""))
    for revision in revisions_with_figures:
        if type(revision) is Revision:
            path = revision.figure.path
        elif type(revision) is ExplanationRevision:
            path = revision.explanation_figure.path
        file_hexdigest = get_hexdigest(path)
        if not file_hexdigest or \
           not file_hexdigest in hashes:
            continue
        full_path = hashes[file_hexdigest]
        relative_path = full_path.replace(settings.MEDIA_ROOT, '')
        figure = Figure()
        figure.figure.name = relative_path
        figure.save()
        revision.figures.add(figure)

def backward(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0099_figures'),
    ]

    operations = [
        migrations.RunPython(forward,
                             reverse_code=backward)
    ]
