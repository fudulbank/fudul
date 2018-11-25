from django.db import models

class CoreMember(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="core_members")
    background = models.ImageField(upload_to="core_members",
                                   blank=True)
    role = models.CharField(max_length=200)
    twitter = models.URLField(blank=True)

    def __str__(self):
        return self.name

class DonationMessage(models.Model):
    text = models.TextField()
    language_choices = (
        ('ar', 'العربية'),
        ('en', 'الإنجليزية')
    )
    language = models.CharField(max_length=2,
                                choices=language_choices,
                                default='en')
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return str(self.pk)
