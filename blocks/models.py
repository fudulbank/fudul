from django.db import models
from django.contrib.auth.models import User
from accounts.models import College, Batch, Institution
from .managers import CategoryQuerySet
from datetime import datetime
import accounts.utils

class Source(models.Model):
    name = models.CharField(max_length=100)
    exam = models.ForeignKey('Exam', null=True)
    submission_date = models.DateTimeField(auto_now_add=True, null=True)

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
    objects = CategoryQuerySet.as_manager()

    def get_parent_categories(self):
        parent_categories = []
        parent_category = self.parent_category
        while parent_category:
            parent_categories.append(parent_category)
            parent_category = parent_category.parent_category

        return parent_categories

    def can_user_access(self, user):
        if user.is_superuser:
            return True

        user_college = accounts.utils.get_user_college(user)
        if not user_college:
            return False

        category = self
        while category:
            if category.college_limist.exists() and \
               not category.college_limit.filter(pk=user_college.pk).exists():
                return False
            category = category.parent_category

        return True

    def get_slugs(self):
        slugs = self.slug
        for parent_category in self.get_parent_categories():
            slugs = parent_category.slug + '/' + slugs

        return slugs

    def __str__(self):
        return self.name


class Exam(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category,related_name='exams')
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    batches_allowed_to_take = models.ForeignKey(Batch, null=True, blank=True)

    def get_question_count(self):
        return Question.objects.filter(subjects__exam=self).distinct().count()

    def __str__(self):
        return self.name


class Subject(models.Model):
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
status_choices = (
    ('C','complete'),
    ('S', 'spelling error'),
    ('A', 'incomplete answers'),
    ('Q', 'incomplete question'),

)


class Question(models.Model):
    sources = models.ManyToManyField(Source, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True)
    figure = models.ImageField(upload_to="exams/question"
                                        "_image", blank=True, null=True)
    exam_type = models.CharField(max_length=1, choices=question_type_choices,
                                 verbose_name="type", default="")
    is_deleted = models.BooleanField(default=False)
    status = models.CharField(max_length=1, choices=status_choices,default="")

    def __str__(self):
        return self.status

    def get_latest_approved_revision(self):
        return self.revision_set.filter(is_approved=True,is_deleted=False).order_by('-approval_date').first()

    def get_latest_revision(self):
        return self.revision_set.filter(is_approved=False,is_deleted=False).order_by('-submission_date').first()


class Revision (models.Model):
    question = models.ForeignKey(Question)
    submitter = models.ForeignKey(User, null=True, blank=True)
    text = models.TextField()
    explanation = models.TextField(default="", blank=True)
    is_approved = models.BooleanField(default=False)
    submission_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_approved:
            self.approval_date = datetime.now()
        super(Revision, self).save(*args, **kwargs)

    def __str__(self):
        return self.text


class Choice(models.Model):
    text = models.CharField(max_length=200)
    is_answer = models.BooleanField(default=False)
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE,null=True)

    def __str__(self):
        return self.text

