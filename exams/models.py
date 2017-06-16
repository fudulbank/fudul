from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from accounts.models import College, Batch
from .managers import CategoryQuerySet
import accounts.utils

class Source(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey('Category')
    submission_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    slug = models.SlugField(max_length=50)
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="category_images",
                              blank=True)
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

        parent_categories.reverse()
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
        slugs = ""
        for parent_category in self.get_parent_categories():
            slugs =  slugs + parent_category.slug + '/'

        slugs += self.slug 

        return slugs

    def __str__(self):
        return self.name


class Exam(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category,related_name='exams')
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    batches_allowed_to_take = models.ForeignKey(Batch, null=True, blank=True)

    def get_sources(self):
        sources = Source.objects.none()
        category = self.category
        while category:
            sources |= category.source_set.all()
            category = category.parent_category
        return sources

    def can_user_edit(self, user):
        if user.is_superuser:
            return True

        category = self.category
        while category:
            if category.privileged_teams.filter(members__pk=user.pk).exists():
                return True
            category = category.parent_category

        return False

    def get_question_count(self):
        return Question.objects.filter(subjects__exam=self).distinct().count()

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=100)
    exam = models.ForeignKey(Exam)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


exam_type_choices = (
    ('FINAL', 'Final'),
    ('MIDTERM', 'Midterm'),
    ('OSPE','OSPE'),
)

status_choices = (
    ('COMPLETE','Complete and valid question'),
    ('WRITING_ERROR', 'Writing errors'),
    ('INCOMPLETE_ANSWERS', 'Incomplete answers'),
    ('INCOMPLETE_QUESTION', 'Incomplete question'),
    ('UNSOLVED', 'Unsolved question'),

)

class Question(models.Model):
    sources = models.ManyToManyField(Source, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True)
    figure = models.ImageField(upload_to="question_images",
                               blank=True)
    exam_type = models.CharField(max_length=15,
                                 choices=exam_type_choices)
    is_deleted = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=status_choices)

    def __str__(self):
        return self.status

    def get_exam(self):
        if self.subjects.exists():
            return self.subjects.first().exam

    def get_latest_approved_revision(self):
        return self.revision_set.filter(is_approved=True,is_deleted=False).order_by('-approval_date').first()

    def get_latest_revision(self):
        return self.revision_set.filter(is_deleted=False).order_by('-submission_date').first()

    def get_ultimate_latest_revision(self):
        if self.get_latest_approved_revision() is not None:
            return self.get_latest_approved_revision()
        else:
            return self.get_latest_revision()


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
            self.approval_date = timezone.now()
        super(Revision, self).save(*args, **kwargs)

    def __str__(self):
        return self.text


class Choice(models.Model):
    text = models.CharField(max_length=200)
    is_answer = models.BooleanField("Right answer?", default=False)
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE,null=True)

    def __str__(self):
        return self.text
