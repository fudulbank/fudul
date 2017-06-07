from django.db import models
from accounts.models import College
from django.contrib.auth.models import User
# Create your models here.


class Year(models.Model):
    name = models.CharField(max_length=100)
    college = models.ForeignKey(College)

    def __unicode__(self):
        return self.name

#% better name than "Block"


class Block(models.Model):
    submitter = models.ForeignKey(User, null=True, blank=True)
    name = models.CharField(max_length=100)
    year = models.ForeignKey(Year)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name


class Subject(models.Model):
    submitter = models.ForeignKey(User, null=True, blank=True)
    name = models.CharField(max_length=100)
    block = models.ForeignKey(Block, null=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)


def __unicode__(self):
        return self.name


question_type_choices = (
    ('F', 'Final'),
    ('M', 'Midterm'),
)


class Question(models.Model):

    submitter = models.ForeignKey(User, null=True, blank=True)
    batch_choices = [(i, i) for i in range(19)]
    subject = models.ForeignKey(Subject)
    batch = models.IntegerField(choices=batch_choices)
    text = models.CharField(max_length=200)
    explanation= models.TextField(null=True, blank=True)
    figure = models.FileField(upload_to="blocks/question"
                                        "_image", blank=True, null=True)
    type = models.CharField(max_length=1, choices=question_type_choices,
                            verbose_name="type", default="")
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name


class Choice(models.Model):
    is_answer = models.BooleanField(default=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)

    def __unicode__(self):
        return self.text