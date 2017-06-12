from django.db import models
from django.contrib.auth.models import User
from accounts.models import College, Batch, Institution
from datetime import datetime


class Year(models.Model):
    name = models.CharField(max_length=100)
    college = models.ForeignKey(College)

    def __str__(self):
        return self.name


class Source(models.Model):
    name = models.CharField(max_length=100)
    college = models.ForeignKey(College)

    def __str__(self):
        return self.name


class Category(models.Model):
    slug = models.SlugField(max_length=50, verbose_name="url")
    name = models.CharField(max_length=100)
    college_limit = models.ManyToManyField(College, blank=True)
    parent_category = models.ForeignKey('self', null=True, blank=True,
                                        related_name="children",
                                        on_delete=models.SET_NULL,
                                        default=None)


    def __str__(self):
        return self.name


class Exam(models.Model):
    submitter = models.ForeignKey(User, null=True, blank=True)
    name = models.CharField(max_length=100)
    parent_category = models.ForeignKey(Category,related_name='exams')
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    batches_allowed_to_take = models.ForeignKey(Batch, null=True, blank=True)

    def __str__(self):
        return self.name


class Subject(models.Model):
    submitter = models.ForeignKey(User, null=True, blank=True)
    name = models.CharField(max_length=100)
    exam = models.ForeignKey(Exam, null=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


question_type_choices = (
    ('F', 'Final'),
    ('M', 'Midterm'),
)


class Question(models.Model):
    source = models.ManyToManyField(Source,default='',blank=True)
    subject = models.ForeignKey(Subject)
    figure = models.FileField(upload_to="exams/question"
                                        "_image", blank=True, null=True)
    exam_type = models.CharField(max_length=1, choices=question_type_choices,
                                 verbose_name="type", default="")
    is_deleted = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name


class Revision (models.Model):
    question = models.ForeignKey(Question)
    submitter = models.ForeignKey(User, null=True, blank=True)
    text = models.TextField()
    explanation = models.TextField(null=True, blank=True, verbose_name="answer_explanation")
    is_approved = models.BooleanField(default=False)
    submission_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateField(blank=True, null=True, verbose_name="Approval_date")
    is_deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_approved:
            self.approval_date = datetime.now()
        super(Revision, self).save(*args, **kwargs)

    # def __init__(self, *args, **kwargs):
    #     super(Revision, self).__init__(*args, **kwargs)
    #     self.old_published = self.approval_date
    #
    # def save(self, *args, **kwargs):
    #     if self.old_published != self.approval_date and self.approval_date:
    #         self.pub_date = datetime.now()
    #     super(Revision, self).save(*args, **kwargs)


class Choice(models.Model):
    text = models.CharField(max_length=200)
    is_answer = models.BooleanField(default=False)
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE,null=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name

