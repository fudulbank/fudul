from django.db import models
from django.contrib.auth.models import User
from ckeditor_uploader.fields import RichTextUploadingField


target_choices = [('INSTITUTIONS', 'Per institutions'),
                  ('COLLEGES', 'Per colleges'),
                  ('BATCHES', 'Per batch'),
                  ('ALL', 'All confirmed users')]

from_addresses = [('noreply@fudulbank.com', 'noreply@fudulbank.com'),
                  ('support@fudulbank.com', 'support@fudulbank.com')]

status_choices = [('PENDING', 'Pending'),
                  ('SENT', 'Sent'),
                  ('PROCESSING', 'Processing')]

class Message(models.Model):
    from_address = models.EmailField(choices=from_addresses)
    subject = models.CharField(max_length=140)
    body = RichTextUploadingField(default='', blank=True)

    target = models.CharField(max_length=20, choices=target_choices, default="ALL")
    institutions = models.ManyToManyField('accounts.Institution', blank=True)
    colleges = models.ManyToManyField('accounts.College', blank=True)
    batches = models.ManyToManyField('accounts.Batch', blank=True)

    status = models.CharField(max_length=20, default="PENDING", choices=status_choices)
    submitter = models.ForeignKey(User)
    submission_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.subject
