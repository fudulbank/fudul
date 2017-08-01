from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from accounts.models import College, Batch
from . import managers
import accounts.utils
import textwrap


class Source(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey('Category')
    parent_source = models.ForeignKey('self', null=True, blank=True,
                                      related_name="children",
                                      on_delete=models.SET_NULL)
    submission_date = models.DateTimeField(auto_now_add=True)
    objects = managers.SourceQuerySet.as_manager()

    def __str__(self):
        return self.name

class Status(models.Model):
    name = models.CharField(max_length=100)
    # code_name is something more stable than 'name'
    code_name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class ExamType(models.Model):
    name = models.CharField(max_length=100)
    # code_name is something more stable than 'name'
    code_name = models.CharField(max_length=50)
    category = models.ForeignKey('Category')

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
    objects = managers.CategoryQuerySet.as_manager()

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
            if category.college_limit.exists() and \
               not category.college_limit.filter(pk=user_college.pk).exists():
                return False
            category = category.parent_category

        return True

    def is_user_editor(self, user):
        if user.is_superuser:
            return True

        category = self
        while category:
            if category.privileged_teams.filter(access='editors',
                                                members__pk=user.pk).exists():
                return True
            category = category.parent_category

        return False

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

    def get_exam_types(self):
        exam_types = ExamType.objects.none()
        category = self.category
        while category:
            exam_types |= category.examtype_set.all()
            category = category.parent_category
        return exam_types

    def can_user_edit(self, user):
        if user.is_superuser:
            return True

        category = self.category
        while category:
            if category.privileged_teams.filter(members__pk=user.pk).exists():
                return True
            category = category.parent_category

        return False

    def get_questions(self):
        return Question.objects.undeleted()\
                               .filter(subjects__exam=self).distinct()

    def get_complete_questions(self):
        pks = Revision.objects.per_exam(self)\
                              .filter(statuses__code_name='COMPLETE',
                                      is_last=True)\
                              .values_list('question__pk', flat=True)
        questions = Question.objects.undeleted().filter(pk__in=pks)
        return questions

    def get_incomplete_questions(self):
        pks = Revision.objects.per_exam(self)\
                              .filter(is_last=True)\
                              .exclude(statuses__code_name='COMPLETE')\
                              .values_list('question__pk', flat=True)
        questions = Question.objects.undeleted().filter(pk__in=pks)
        return questions

    def get_approved_latest_revisions(self):
        return Revision.objects.select_related('question', 'submitter')\
                               .per_exam(self)\
                               .filter(is_last=True, is_approved=True)

    def get_pending_latest_revisions(self):
        return Revision.objects.select_related('question', 'submitter')\
                               .per_exam(self)\
                               .filter(is_last=True, is_approved=False)

    def get_approved_questions(self):
        pks = self.get_approved_latest_revisions().values_list('question__pk', flat=True)
        questions = Question.objects.undeleted().filter(pk__in=pks)
        return questions

    def get_pending_questions(self):
        pks = self.get_pending_latest_revisions().values_list('question__pk', flat=True)
        questions = Question.objects.undeleted().filter(pk__in=pks)
        return questions

    def get_questions_with_writing_error(self):
        pks = Revision.objects.per_exam(self)\
                              .filter(is_last=True, status='WRITING_ERROR')\
                              .values_list('question__pk',flat=True)
        questions = Question.objects.undeleted().filter(pk__in=pks)
        return questions

    def get_questions_with_incomplete_question(self):
        pks = Revision.objects.per_exam(self)\
                              .filter(is_last=True, status='INCOMPLETE_QUESTION')\
                              .values_list('question__pk',flat=True)
        questions = Question.objects.undeleted().filter(pk__in=pks)
        return questions

    def get_questions_with_incomplete_answers(self):
        pks = Revision.objects.per_exam(self)\
                              .filter(is_last=True, status='INCOMPLETE_ANSWERS')\
                              .values_list('question__pk',flat=True)
        questions = Question.objects.undeleted().filter(pk__in=pks)
        return questions

    def get_unsolved_questions(self):
        pks = Revision.objects.per_exam(self)\
                              .filter(is_last=True, status='UNSOLVED')\
                              .values_list('question__pk',flat=True)
        questions = Question.objects.undeleted().filter(pk__in=pks)
        return questions

    def get_unsolved_questions(self):
        pks = Revision.objects.filter(question__subjects__exam=self,
                                      is_last=True)\
                              .exclude(choice__is_answer=True)\
                              .distinct()\
                              .values_list('question__pk', flat=True)
        questions = Question.objects.undeleted().filter(pk__in=pks)
        return questions

    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=100)
    exam = models.ForeignKey(Exam)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    objects = managers.SubjectQuerySet.as_manager()
    def __str__(self):
        return self.name

status_choices = (
    ('COMPLETE','Complete and valid question'),
    ('WRITING_ERROR', 'Writing errors'),
    ('INCOMPLETE_ANSWERS', 'Incomplete answers'),
    ('INCOMPLETE_QUESTION', 'Incomplete question'),
    ('UNSOLVED', 'Unsolved question'),
)

class Question(models.Model):
    sources = models.ManyToManyField(Source, blank=True)
    subjects = models.ManyToManyField(Subject)
    exam_types = models.ManyToManyField(ExamType)
    is_deleted = models.BooleanField(default=False)
    statuses = models.ManyToManyField(Status)
    objects = managers.QuestionQuerySet.as_manager()
    parent_question = models.ForeignKey('self', null=True, blank=True,
                                        related_name="children",
                                        on_delete=models.SET_NULL,
                                        default=None)

    def __str__(self):
        latest_revision = self.get_latest_revision()
        return textwrap.shorten(latest_revision.text, 70,
                                placeholder='...')

    def is_user_creator(self, user):
        first_revision = self.revision_set.order_by("submission_date").first()
        return first_revision.submitter == user

    def get_exam(self):
        if self.subjects.exists():
            return self.subjects.first().exam

    def get_latest_approved_revision(self):
        return self.revision_set.filter(is_approved=True,is_deleted=False).order_by('-approval_date').first()

    def get_latest_revision(self):
        return self.revision_set.filter(is_deleted=False).order_by('-submission_date').first()

    def get_session_url(self, session):
        category = session.exam.category
        slugs = category.get_slugs()
        return reverse('exams:show_session', args=(slugs,
                                                   session.exam.pk,
                                                   session.pk,
                                                   self.pk))


class Revision(models.Model):
    question = models.ForeignKey(Question)
    submitter = models.ForeignKey(User, null=True, blank=True)
    text = models.TextField()
    statuses = models.ManyToManyField(Status)
    figure = models.ImageField(upload_to="revision_images",
                               blank=True)
    explanation = models.TextField(default="", blank=True)
    is_approved = models.BooleanField(default=False)
    is_first = models.BooleanField(default=False)
    is_last = models.BooleanField(default=False)
    submission_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    objects = managers.RevisionQuerySet.as_manager()

    def has_right_answer(self):
        return self.choice_set.filter(is_answer=True).exists()

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
    objects = managers.ChoiceQuerySet.as_manager()

    def __str__(self):
        return self.text


questions_choices = (
    ('U','Unused'),
    ('I', 'Incorrect'),
    ('A', 'All'),
    ('C', 'Custom'),
    ('R','Random')
)

class Session(models.Model):
    solved = models.BooleanField("Solved Questions", default=False)
    number_of_questions = models.PositiveIntegerField(default=0)
    sources = models.ManyToManyField(Source, blank=True)
    subjects = models.ManyToManyField(Subject)
    exam = models.ForeignKey(Exam)
    questions = models.ManyToManyField(Question)
    exam_types = models.ManyToManyField(ExamType)
    submitter = models.ForeignKey(User)
    right_answers=models.PositiveIntegerField(default=0)
    is_marked = models.ManyToManyField(Question,related_name='marked')
    marked = models.BooleanField("Marked", default=False)
    unsloved = models.BooleanField("Unsolved", default=False)
    incoorect = models.BooleanField("Incorrect", default=False)
    question_filter= models.CharField(max_length=1,choices=questions_choices,blank=False,default=None)


    def score (self):
        return self.answer_set.filter(choice__is_answer=True).count()/self.number_of_questions*100

    def correct_answers (self):
        return self.answer_set.filter(choice__is_answer=True).count()

    def finished (self,user):
        if self.answer_set.filter(choice__isnull=True,session__submitter=user).exist:
            return False

    def get_question_sequence(self, question):
        return self.questions.filter(pk__lte=question.pk).count()

    def get_unused_questions(self):
        return self.questions.order_by('pk').exclude(answer__isnull=False)

class Answer(models.Model):
    session = models.ForeignKey(Session)
    question = models.ForeignKey(Question)
    choice = models.ForeignKey(Choice,null=True)
    is_marked = models.BooleanField("is marked ?", default=False)
