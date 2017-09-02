from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from accounts.models import College, Batch
from . import managers
import accounts.utils
import textwrap
from ckeditor_uploader.fields import RichTextUploadingField

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
    objects = managers.MetaInformationQuerySet.as_manager()

    def __str__(self):
        return "{} ({})".format(self.name, self.question_set.approved().count())


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

        if self.is_user_editor(user):
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
            if category.privileged_teams.filter(members__pk=user.pk).exists():
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
        parent_categories = self.get_parent_categories()
        names = [category.name for category in parent_categories] + \
                [self.name]
        return "/".join(names)

class Exam(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category,related_name='exams')
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    batches_allowed_to_take = models.ForeignKey(Batch, null=True, blank=True)
    exam_types = models.ManyToManyField('ExamType', blank=True)
    credits = RichTextUploadingField(default='')
    objects = managers.ExamQuerySet.as_manager()

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

    def get_approved_latest_revisions(self):
        return Revision.objects.select_related('question', 'submitter')\
                               .undeleted()\
                               .per_exam(self)\
                               .filter(is_last=True, is_approved=True)

    def get_pending_latest_revisions(self):
        return Revision.objects.select_related('question', 'submitter')\
                               .undeleted()\
                               .per_exam(self)\
                               .filter(is_last=True, is_approved=False)

    def get_user_answered_questions(self, user):
        return Question.objects.filter(answer__session__submitter=user).distinct()


    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=100)
    exam = models.ForeignKey(Exam)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    objects = managers.MetaInformationQuerySet.as_manager()

    def __str__(self):
        return "{} ({})".format(self.name, self.question_set.approved().count())

class Question(models.Model):
    sources = models.ManyToManyField(Source, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True)
    exam = models.ForeignKey(Exam)
    exam_types = models.ManyToManyField(ExamType, blank=True)
    is_deleted = models.BooleanField(default=False)
    # `global_sequence` is a `pk` field that accounts for question
    # parents and children.  It is used to determine the sequence of
    # question within sessions.
    global_sequence = models.PositiveIntegerField(null=True, blank=True)
    statuses = models.ManyToManyField(Status)
    marking_users = models.ManyToManyField(User, blank=True,
                                           related_name="marked_questions")
    objects = managers.QuestionQuerySet.as_manager()
    parent_question = models.OneToOneField('self', null=True,
                                           blank=True,
                                           related_name="child_question",
                                           on_delete=models.SET_NULL,
                                           default=None)

    def __str__(self):
        latest_revision = self.get_latest_revision()
        return textwrap.shorten(latest_revision.text, 70,
                                placeholder='...')

    def is_user_creator(self, user):
        first_revision = self.revision_set.order_by("submission_date").first()
        return first_revision.submitter == user

    def was_solved_in_session(self, session):
        if session.session_mode == 'SOLVED':
            return True
        else:
            return Answer.objects.filter(session=session, question=self).exists()

    def get_latest_approved_revision(self):
        return self.revision_set.filter(is_approved=True, is_deleted=False)\
                                .order_by('-pk')\
                                .first()

    def get_latest_revision(self):
        return self.revision_set.filter(is_deleted=False)\
                                .order_by('-submission_date')\
                                .first()

    def get_correct_others(self):
        correct_user_pks = Answer.objects.filter(question=self,
                                                 choice__is_right=True)\
                                         .values_list('session__submitter', flat=True)
        total_user_pks = Answer.objects.filter(question=self)\
                                       .values_list('session__submitter', flat=True)
        correct_users = User.objects.filter(pk__in=correct_user_pks).count()
        total_users = User.objects.filter(pk__in=total_user_pks).count()
        return correct_users / total_users * 100

    def get_session_url(self, session):
        category = session.exam.category
        slugs = category.get_slugs()
        return reverse('exams:show_session', args=(slugs,
                                                   session.exam.pk,
                                                   session.pk,
                                                   self.pk))

    def get_contributors(self):
        contributors = []
        for revision in self.revision_set.order_by('pk'):
            if not revision.submitter in contributors:
                contributors.append(revision.submitter)
        return contributors

    def get_tree(self):
        """Get a sorted list of question parents and children."""
        tree = []

        parent_question = self.parent_question
        while parent_question:
            tree = [parent_question] + tree
            parent_question = parent_question.parent_question

        tree.append(self)

        question = self
        while hasattr(question, 'child_question'):
            tree.append(question.child_question)
            question = question.child_question

        return tree




class Revision(models.Model):
    question = models.ForeignKey(Question)
    submitter = models.ForeignKey(User, null=True, blank=True)
    text = models.TextField()
    statuses = models.ManyToManyField(Status)
    figure = models.ImageField(upload_to="revision_images",
                               blank=True)
    explanation = models.TextField(default="", blank=True)
    explanation_figure = models.ImageField(upload_to="explanation_images",
                                           blank=True)
    is_approved = models.BooleanField(default=False)
    is_first = models.BooleanField(default=False)
    is_last = models.BooleanField(default=False)
    submission_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    objects = managers.RevisionQuerySet.as_manager()
    reference = models.TextField(default="", blank=True)
    change_summary = models.TextField(default="", blank=True)
    is_contribution = models.BooleanField(default=False)

    def has_right_answer(self):
        return self.choice_set.filter(is_right=True).exists()

    def save(self, *args, **kwargs):
        if self.is_approved:
            self.approval_date = timezone.now()
        super(Revision, self).save(*args, **kwargs)

    def __str__(self):
        return self.text



class Choice(models.Model):
    text = models.CharField(max_length=200)
    is_right = models.BooleanField("Right answer?", default=False)
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE,null=True)
    objects = managers.ChoiceQuerySet.as_manager()

    def __str__(self):
        return self.text


questions_choices = (
    ('UNUSED','Unused'),
    ('INCORRECT', 'Incorrect'),
    ('MARKED', 'Marked'),
    ('ALL','All'),
)

session_mode_choices = (
    ('EXPLAINED', 'Explained'),
    ('UNEXPLAINED', 'Unexplained'),
    ('SOLVED', 'Solved'),
)

class Session(models.Model):
    session_mode = models.CharField(max_length=20, choices=session_mode_choices, default=None)
    number_of_questions = models.PositiveIntegerField(null=True)
    sources = models.ManyToManyField(Source, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True)
    exam = models.ForeignKey(Exam)
    questions = models.ManyToManyField(Question, blank=True)
    exam_types = models.ManyToManyField(ExamType, blank=True)
    submitter = models.ForeignKey(User)
    question_filter = models.CharField(max_length=20, choices=questions_choices, default=None)
    submission_date = models.DateTimeField(auto_now_add=True)

    objects = managers.SessionQuerySet.as_manager()

    def get_score(self):
        if not self.number_of_questions ==0 :
            total = self.get_total_question_count()
            correct = self.get_correct_answer_count()
            return round(correct / total * 100, 2)

    def get_total_question_count(self):
        return self.questions.approved().count()

    def get_used_questions_count(self):
        return self.answer_set.distinct() \
            .count()
        
    def get_correct_answer_count(self):
        return self.answer_set.of_undeleted_questions()\
                              .filter(choice__is_right=True)\
                              .distinct()\
                              .count()

    def has_finished(self):
        return not self.get_unused_questions().exists()


    def get_question_sequence(self, question):
        return self.questions.approved()\
                             .filter(global_sequence__lte=question.pk)\
                             .count()

    def get_unused_questions(self):
        return self.questions.approved()\
                             .exclude(answer__session=self)\
                             .order_by('global_sequence')\
                             .distinct()

    def has_question(self, question):
        return self.questions.approved()\
                             .filter(pk=question.pk)\
                             .exists()

    def get_current_question(self, question_pk=None):
        # If a question PK is given, show it.  Otheriwse show the first
        # session unused question.  Otherwise, show the first session
        # question.
        if question_pk:
            current_question = get_object_or_404(self.questions.approved(), pk=question_pk)
        elif not self.has_finished():
            current_question = self.get_unused_questions().first()
        else:
            current_question = self.questions.approved()\
                                             .order_by('global_sequence')\
                                             .first()

        return current_question

    def can_user_access(self, user):
        return self.submitter == user or user.is_superuser

class Answer(models.Model):
    session = models.ForeignKey(Session)
    question = models.ForeignKey(Question)
    choice = models.ForeignKey(Choice,null=True)
    is_marked = models.BooleanField("is marked ?", default=False)
    objects = managers.AnswerQuerySet.as_manager()
