from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.core.cache import cache
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.urls import reverse
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
import datetime
import textwrap
import re

from . import managers
from ckeditor_uploader.fields import RichTextUploadingField
from notifications.models import Notification
from notifications.signals import notify
import accounts.utils


class Source(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey('Category',
                                 on_delete=models.SET_NULL,
                                 null=True)
    parent_source = models.ForeignKey('self', null=True, blank=True,
                                      related_name="children",
                                      on_delete=models.CASCADE)
    submission_date = models.DateTimeField(auto_now_add=True)
    objects = managers.SourceQuerySet.as_manager()

    def get_recent_submission_count(self):
        back_30_days = timezone.now().date() - datetime.timedelta(30)
        return self.question_set.filter(revision__is_first=True,
                                        revision__submission_date__gte=back_30_days)\
                                .distinct()\
                                .count()

    def __str__(self):
        return self.name

class Issue(models.Model):
    name = models.CharField(max_length=100)
    # code_name is something more stable than 'name'
    code_name = models.CharField(max_length=50)
    is_blocker = models.BooleanField(default=False)

    def get_selector(self):
        return 'i-' + str(self.pk)

    def __str__(self):
        if self.is_blocker:
            blocker_str = "blocker"
        else:
            blocker_str = "non-blocker"

        return "{} ({})".format(self.name, blocker_str)

class ExamType(models.Model):
    name = models.CharField(max_length=100)
    # code_name is something more stable than 'name'
    code_name = models.CharField(max_length=50)
    objects = managers.MetaInformationQuerySet.as_manager()

    def __str__(self):
        return self.name

class Category(models.Model):
    slug = models.SlugField(max_length=50)
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="category_images",
                              blank=True)
    group_limit = models.ManyToManyField('accounts.Group', blank=True)
    parent_category = models.ForeignKey('self', null=True, blank=True,
                                        related_name="children",
                                        on_delete=models.SET_NULL,
                                        default=None)
    is_listed = models.BooleanField("This category is listed upon showing categories and on the sidebar",
                                    default=True, blank=True)
    objects = managers.CategoryQuerySet.as_manager()

    def set_slug_cache(self):
        cache_key = f'category_{self.pk}_slug'
        cached_slugs = cache.get(cache_key)
        if not cached_slugs:
            cache.set(cache_key, self.get_slugs(try_cache=False), None)

    def get_parent_categories(self):
        parent_categories = []
        parent_category = self.parent_category
        while parent_category:
            parent_categories.append(parent_category)
            parent_category = parent_category.parent_category

        parent_categories.reverse()
        return parent_categories

    def can_user_access(self, user, user_group=None):
        if not user.is_authenticated:
            return False
        elif user.is_superuser:
            return True

        if not user_group:
            user_group = accounts.utils.get_user_group(user)
        category = self

        while category:
            if category.group_limit.exists() and \
               (not user_group or \
                not category.group_limit.filter(pk=user_group.pk).exists()):
                return False
            category = category.parent_category

        return True

    def get_slugs(self, try_cache=True):
        if try_cache:
            cache_key = f'category_{self.pk}_slugs'
            cached_slugs = cache.get(cache_key)
            if cached_slugs:
                return cached_slugs

        slugs = ""
        for parent_category in self.get_parent_categories():
            slugs =  slugs + parent_category.slug + '/'

        slugs += self.slug

        return slugs

    def get_absolute_url(self):
        return reverse("exams:show_category",
                       args=(self.get_slugs(),))

    def __str__(self):
        parent_categories = self.get_parent_categories()
        names = [category.name for category in parent_categories] + \
                [self.name]
        return "/".join(names)

class Exam(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, related_name='exams',
                                 null=True,
                                 on_delete=models.SET_NULL)
    is_visible = models.BooleanField(default=True)
    levels_allowed_to_take = models.ManyToManyField('accounts.Level',
                                                    blank=True)
    groups_allowed_to_take = models.ManyToManyField('accounts.Group',
                                                    blank=True)
    exam_types = models.ManyToManyField('ExamType', blank=True)
    credits = RichTextUploadingField(default='', blank=True)
    was_announced = models.BooleanField("This exam was announced and is readily available for users who are not editors",
                                        default=True, blank=True)
    inherits_sources = models.BooleanField("This exam inherits sources from its parent categories",
                                           default=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    objects = managers.ExamQuerySet.as_manager()

    def get_pending_duplicates(self):
        duplicate_with_questions = Duplicate.objects.filter(question__exam=self)\
                                                    .with_undeleted_question()
        duplicate_containers = DuplicateContainer.objects\
                                                 .select_related('primary_question',
                                                                 'primary_question__best_revision')\
                                                 .filter(status="PENDING",
                                                         primary_question__exam=self,
                                                         primary_question__is_deleted=False,
                                                         primary_question__revision__is_deleted=False)\
                                                 .filter(pk__in=duplicate_with_questions.values('container'))\
                                                 .distinct()
        return duplicate_containers

    def get_pending_suggested_changes(self):
        return SuggestedChange.objects.select_related('revision',
                                                      'revision__question')\
                                      .filter(status="PENDING",
                                              revision__is_last=True,
                                              revision__is_deleted=False,
                                              revision__question__exam=self)\
                                      .distinct()

    def get_user_count(self):
        return Session.objects.filter(exam=self)\
                              .values('submitter')\
                              .distinct().count()

    get_user_count.short_description = '# users'

    def get_sources(self):
        sources = Source.objects.none()
        if not self.inherits_sources:
            return sources
        category = self.category
        while category:
            sources |= category.source_set.all()
            category = category.parent_category
        return sources

    def get_editors(self):
        return User.objects.filter(team_memberships__exams=self).distinct()

    def can_user_access(self, user):
        user_group = accounts.utils.get_profile_attr(user, 'group')
        user_level = accounts.utils.get_profile_attr(user, 'level')
        exam_groups = self.groups_allowed_to_take.all()
        exam_levels = self.levels_allowed_to_take.all()

        if (not exam_groups or
            user_group in exam_groups) and \
           (not exam_levels or
            user_level in exam_levels) and \
           self.category.can_user_access(user, user_group):
           return True
        else:
            return False

    def can_user_edit(self, user):
        if user.is_superuser or \
           self.privileged_teams.filter(members__pk=user.pk).exists():
            return True
        else:
            return False

    def get_percentage_of_correct_submitted_answers(self):
        submitted_answers = Answer.objects.filter(session__exam=self,choice__isnull=False).count()
        if not submitted_answers == 0:
            return Answer.objects.filter(session__exam=self,choice__is_right=True).count()/submitted_answers* 100
        else:
            return 0

    def get_absolute_url(self):
        return reverse("exams:create_session",
                       args=(self.category.get_slugs(),
                             self.pk))

    def __str__(self):
        return "{} ({})".format(self.name, self.category)

class ExamDate(models.Model):
    name = models.CharField(max_length=100)
    exam = models.ForeignKey(Exam, related_name='exam_dates',
                             on_delete=models.CASCADE)
    level = models.ForeignKey('accounts.Level',
                              null=True,
                              on_delete=models.SET_NULL,
                              related_name='exam_dates')
    date = models.DateField()

    def __str__(self):
        data_str = self.date.strftime('%Y-%m-%d')
        return "{} on {}".format(self.name, data_str)

class Subject(models.Model):
    name = models.CharField(max_length=100)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    objects = managers.MetaInformationQuerySet.as_manager()

    def get_selector(self):
        return 's-' + str(self.pk)

    def __str__(self):
        return self.name

class Difficulty(models.Model):
    label = models.CharField(max_length=100)
    tooltip = models.TextField()
    upper_limit = models.PositiveIntegerField()
    lower_limit = models.PositiveIntegerField()
    objects = managers.MetaInformationQuerySet.as_manager()

    def __str__(self):
        return self.label

class Question(models.Model):
    sources = models.ManyToManyField(Source, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    exam_types = models.ManyToManyField(ExamType, blank=True)
    is_deleted = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    # `global_sequence` is a `pk` field that accounts for question
    # parents and children.  It is used to determine the sequence of
    # question within sessions.
    global_sequence = models.PositiveIntegerField(null=True, blank=True)
    issues = models.ManyToManyField('Issue', blank=True)
    marking_users = models.ManyToManyField(User, blank=True,
                                           related_name="marked_questions")
    objects = managers.QuestionQuerySet.as_manager()
    parent_question = models.OneToOneField('self', null=True,
                                           blank=True,
                                           related_name="child_question",
                                           on_delete=models.SET_NULL,
                                           default=None)
    best_revision = models.OneToOneField('Revision', null=True, blank=True,
                                         on_delete=models.SET_NULL,
                                         related_name="best_of")
    latest_explanation_revision = models.OneToOneField('ExplanationRevision',
                                                       null=True,
                                                       blank=True,
                                                       on_delete=models.SET_NULL,
                                                       related_name="latst_of")
    assigned_editor = models.ForeignKey(User, null=True, blank=True,
                                        on_delete=models.SET_NULL,
                                        related_name="assigned_questions")
    difficulty = models.ForeignKey(Difficulty, null=True, blank=True,
                                   on_delete=models.SET_NULL)

    # Database-heavy counts
    total_user_count = models.PositiveIntegerField(null=True)
    correct_first_timer_count = models.PositiveIntegerField(null=True)

    def __str__(self):
        latest_revision = self.get_latest_revision()
        if not latest_revision:
            return str(self.pk)
        return textwrap.shorten(latest_revision.text, 70,
                                placeholder='...')

    def get_absolute_url(self):
        return reverse("exams:show_single_question",
                       args=(self.exam.category.get_slugs(),
                             self.exam.pk, self.pk))

    def get_list_revision_url(self):
        return reverse("exams:list_revisions",
                       args=(self.exam.category.get_slugs(),
                             self.exam.pk, self.pk))

    def get_answering_user_count(self):
        user_pks = Answer.objects.filter(choice__question=self)\
                                 .values('session__submitter')
        return User.objects.filter(pk__in=user_pks)\
                           .count()

    def is_incomplete(self):
        latest_revision = self.get_latest_revision()
        if self.issues.filter(is_blocker=True).exists() or \
           not latest_revision.choices.filter(is_right=True).exists() or \
           latest_revision.choices.count() >= 1:
            return True
        else:
            return False

    def is_user_creator(self, user):
        first_revision = self.revision_set.order_by("submission_date").first()
        return first_revision.submitter == user

    def was_solved_in_session(self, session):
        if not session.is_examinable():
            return True
        else:
            return Answer.objects.filter(session=session, question=self).exists()

    def get_best_revision(self):
        return self.get_latest_approved_revision() or \
               self.get_latest_revision_by_editor() or \
               self.get_latest_revision()

    def get_latest_approved_revision(self):
        return self.revision_set.filter(is_approved=True, is_deleted=False)\
                                .order_by('submission_date')\
                                .last()

    def get_latest_revision_by_editor(self):
        return self.revision_set.filter(is_deleted=False, is_contribution=False)\
                                .order_by('submission_date')\
                                .last()

    def get_latest_revision(self):
        return self.revision_set.filter(is_deleted=False)\
                                .order_by('submission_date')\
                                .last()

    def get_latest_explanation_revision(self):
        return self.explanation_revisions\
                   .filter(is_deleted=False)\
                   .order_by('submission_date')\
                   .last()

    def get_correct_percentage(self):
        if self.total_user_count:
            result = self.correct_first_timer_count / self.total_user_count * 100
            return round(result)
        else:
            return 0

    def get_contributors(self):
        contributors = []
        for revision in self.revision_list:
            if revision.submitter and not revision.submitter in contributors:
                contributors.append(revision.submitter)

        contributors.sort(key=lambda user: user.pk, reverse=True)

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
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    submitter = models.ForeignKey(User, null=True, blank=True,
                                  on_delete=models.SET_NULL)
    text = models.TextField()
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
    #NOTE:colud be a model instead
    approved_by = models.ForeignKey(User,related_name="approved_revision",
                                    null=True,blank=True,
                                    on_delete=models.SET_NULL)

    target_notifications = GenericRelation('notifications.Notification',
                                           content_type_field='target_content_type',
                                           object_id_field='target_object_id',
                                           related_query_name="target_revisions")
    actor_notifications = GenericRelation('notifications.Notification',
                                           content_type_field='actor_content_type',
                                           object_id_field='actor_object_id',
                                           related_query_name="acting_revisions")
    figures = models.ManyToManyField('Figure', blank=True)
    choices = models.ManyToManyField('Choice', blank=True, related_name="revision_set")

    def get_previous(self):
        return self.question.revision_set\
                            .filter(is_deleted=False,
                                    submission_date__lt=self.submission_date)\
                            .order_by('submission_date').last()

    def get_right_choice(self):
        return self.choices.filter(is_right=True).first()

    def has_right_answer(self):
        return self.choices.filter(is_right=True).exists()

    def get_relevant_highlight(self, session):
        return Highlight.objects.select_related('revision')\
                                .filter(revision__question=self.question,
                                        session=session)\
                                .last()

    def get_shorten_text(self):
        return textwrap.shorten(self.text, 70,
                                placeholder='...')

    def save(self, *args, **kwargs):
        if self.is_approved:
            self.approval_date = timezone.now()
        super(Revision, self).save(*args, **kwargs)

    def unnotify_submitter(self, user):
        Notification.objects.filter(verb='approved',
                                    target_revisions=self).delete()

    def notify_submitter(self, actor):
        if not self.approved_by:
            return

        title = "{} was approved".format(str(self))
        user_credit = accounts.utils.get_user_credit(self.approved_by)
        description = "Your edit to question #{} in {} was approved by {}".format(self.question.pk,
                                                                                  self.question.exam.name,
                                                                                  user_credit)
        url = self.get_absolute_url()
        notify.send(self.approved_by, recipient=self.submitter,
                    target=self, verb='approved', title=title,
                    description=description, url=url)

    def get_absolute_url(self):
        return reverse("exams:list_revisions",
                       args=(self.question.exam.category.get_slugs(),
                             self.question.exam.pk, self.question.pk))

    def __str__(self):
        if self.question:
            return "Revision #{} of Q#{}".format(self.pk, self.question.pk)
        else:
            return "Revision #{}".format(self.pk)

class Choice(models.Model):
    text = models.CharField(max_length=255)
    is_right = models.BooleanField("Right answer?", default=False)
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE,null=True)
    question = models.ForeignKey(Question,  null=True, on_delete=models.CASCADE)
    objects = managers.ChoiceQuerySet.as_manager()

    def __str__(self):
        return self.text


questions_choices = (
    ('ALL','All complete'),
    ('UNUSED','Unused'),
    ('INCORRECT', 'Incorrect'),
    ('SKIPPED', 'Skipped'),
    ('MARKED', 'Marked'),
    ('INCOMPLETE', 'Incomplete'),
)

session_mode_choices = (
    ('EXPLAINED', 'Explained'),
    ('UNEXPLAINED', 'Unexplained'),
    ('SOLVED', 'Solved'),
    ('INCOMPLETE', 'Incomplete'),
)

class Session(models.Model):
    session_mode = models.CharField(max_length=20, choices=session_mode_choices, default='EXPLAINED')
    parent_session = models.ForeignKey('self',
                                       on_delete=models.SET_NULL,
                                       related_name="children",
                                       null=True,
                                       blank=True)
    examinee_name = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=100, blank=True)
    share_results = models.BooleanField(default=True)
    secret_key = models.CharField(max_length=10)
    number_of_questions = models.PositiveIntegerField(null=True)
    sources = models.ManyToManyField(Source, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True)
    difficulties = models.ManyToManyField(Difficulty, blank=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    questions = models.ManyToManyField(Question, blank=True)
    exam_types = models.ManyToManyField(ExamType, blank=True)
    submitter = models.ForeignKey(User, on_delete=models.CASCADE)
    question_filter = models.CharField(max_length=20, choices=questions_choices, default=None)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    is_automatic = models.BooleanField(default=False)
    actor_notifications = GenericRelation('notifications.Notification',
                                          content_type_field='actor_content_type',
                                          object_id_field='actor_object_id',
                                          related_query_name="sessions")

    # We store these values instead of calculating them dynamically,
    # because this can tremendously enhance performance.
    unused_question_count = models.PositiveIntegerField(default=0)
    correct_answer_count = models.PositiveIntegerField(default=0)
    incorrect_answer_count = models.PositiveIntegerField(default=0)
    skipped_answer_count = models.PositiveIntegerField(default=0)

    objects = managers.SessionQuerySet.as_manager()

    def get_used_question_count(self):
        return self.correct_answer_count + \
            self.incorrect_answer_count + \
            self.skipped_answer_count

    def get_total_question_count(self):
        return self.unused_question_count + self.get_used_question_count()

    def get_score(self):
        try:
            total = self.get_total_question_count()
            correct = self.correct_answer_count
            return round(correct / total * 100, 2)
        except ZeroDivisionError:
            correct = 0
            return correct

    def get_questions(self):
        if self.question_filter == 'INCOMPLETE':
            questions = self.questions.undeleted()
        else:
            questions = self.questions.approved()
        return questions

    def is_examinable(self):
        return self.session_mode not in ['INCOMPLETE', 'SOLVED']

    def get_has_finished(self):
        # Session that are either 'INCOMPLETE' or 'SOLVED' cannot be
        # considered 'finsihed'
        if not self.is_examinable():
            return

        return not self.unused_question_count

    def get_question_sequence(self, question):
        # global_sequence may not be set for freshly created
        # questions.  For these, use pk to calculate sequence.
        if not question.global_sequence:
            return self.get_questions()\
                       .filter(pk__lte=question.pk)\
                       .count()
        else:
            return self.get_questions()\
                       .filter(global_sequence__lte=question.global_sequence)\
                       .count()

    def get_unused_questions(self):
        return self.get_questions()\
                   .exclude(answer__session=self)\
                   .order_by('global_sequence')\
                   .distinct()

    def has_question(self, question):
        return self.get_questions()\
                   .filter(pk=question.pk)\
                   .exists()

    def get_current_question(self, question_pk=None):
        # If a question PK is given, show it.  Otheriwse show the
        # first session unused question.  If all questions were
        # answered, show the first session question.
        if question_pk:
            qs = self.get_questions()
        elif self.unused_question_count:
            qs = self.get_unused_questions()
        else:
            qs = self.get_questions().order_by('global_sequence')

        qs = qs.select_for_show_session()

        if question_pk:
            current_question = get_object_or_404(qs, pk=question_pk)
        else:
            current_question = qs.first()

        return current_question

    def can_user_access(self, user):
        return self.submitter == user or user.is_superuser

    def get_absolute_url(self):
        return reverse("exams:show_session",
                       args=(self.exam.category.get_slugs(),
                             self.exam.pk, self.pk))

    def __str__(self):
        return "Session #{}".format(self.pk)

class Answer(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, null=True,
                               on_delete=models.CASCADE)
    is_first = models.BooleanField("Is this the first time this question was answered by the user?",
                                   blank=True, default=False)
    submission_date = models.DateTimeField(auto_now_add=True, null=True)

    objects = managers.AnswerQuerySet.as_manager()

    class Meta:
        unique_together = ("session", "question")

    def __str__(self):
        return "Answer of Q#{} in S#{}".format(self.question.pk,
                                               self.session.pk)

class Highlight(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, null=True,
                                 on_delete=models.CASCADE)

    # Since revision text and choices are changeable, but we also want
    # to keep the highlights/strikes, let's remember which revision
    # was the user faced with.  In case the text of that revision and
    # the showed revision differs, we won't keep
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE)
    highlighted_text = models.TextField()
    stricken_choices = models.ManyToManyField(Choice, blank=True,
                                              related_name="striking_answers")

    submission_date = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        unique_together = ("session", "question")

    def __str__(self):
        return "Highlight on Q#{} in S#{}".format(self.revision.question.pk,
                                                  self.session.pk)

class AnswerCorrection(models.Model):
    choice = models.OneToOneField(Choice, null=True,
                                  on_delete=models.CASCADE,
                                  related_name="answer_correction")
    supporting_users = models.ManyToManyField(User, blank=True,
                                              related_name="supported_corrections")
    opposing_users = models.ManyToManyField(User, blank=True,
                                            related_name="opposed_corrections")
    submitter = models.ForeignKey(User, on_delete=models.CASCADE)
    justification = models.TextField(default="")
    submission_date = models.DateTimeField(auto_now_add=True)

    target_notifications = GenericRelation('notifications.Notification',
                                           content_type_field='target_content_type',
                                           object_id_field='target_object_id',
                                           related_query_name="target_corrections")
    actor_notifications = GenericRelation('notifications.Notification',
                                           content_type_field='actor_content_type',
                                           object_id_field='actor_object_id',
                                           related_query_name="acting_corrections")

    def unnotify_submitter(self, actor):
        Notification.objects.filter(verb='supported',
                                    target_corrections=self).delete()

    def notify_submitter(self, actor):
        title = "Your correction was supported by another Fuduli!"
        user_credit = accounts.utils.get_user_credit(actor)
        description = "Your correction for question #{} was supported by {}".format(self.choice.question.pk,
                                                                                    user_credit)
        notify.send(actor, recipient=self.submitter, target=self,
                    verb='supported', title=title,
                    description=description, style='support')

    def can_user_delete(self, user, can_user_edit_exam=None):
        # We can pass `can_user_edit_exam` to avoid reterving the
        # result every single time
        if not can_user_edit_exam:
            exam = self.choice.question.exam
            can_user_edit_exam = exam.can_user_edit(user)
        return self.submitter == user or \
            can_user_edit_exam

    def __str__(self):
        return "Correction of Q#{}".format(self.choice.question.pk)

class ExplanationRevision(models.Model):
    question = models.ForeignKey(Question,
                                 related_name="explanation_revisions",
                                 on_delete=models.CASCADE)
    submitter = models.ForeignKey(User, null=True, blank=True,
                                  on_delete=models.SET_NULL,
                                  related_name="submitted_explanations")

    explanation_text = models.TextField(default="")
    reference = models.TextField(default="", blank=True)
    explanation_figure = models.ImageField(upload_to="explanation_images",
                                           blank=True)
    is_contribution = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_first = models.BooleanField(default=False)
    is_last = models.BooleanField(default=False)
    submission_date = models.DateTimeField(auto_now_add=True)

    objects = managers.RevisionQuerySet.as_manager()
    target_notifications = GenericRelation('notifications.Notification',
                                           content_type_field='target_content_type',
                                           object_id_field='target_object_id',
                                           related_query_name="target_explanation_revisions")
    actor_notifications = GenericRelation('notifications.Notification',
                                           content_type_field='actor_content_type',
                                           object_id_field='actor_object_id',
                                           related_query_name="acting_explanation_revisions")
    figures = models.ManyToManyField('Figure', blank=True)

    def get_absolute_url(self):
        return reverse("exams:list_revisions",
                       args=(self.question.exam.category.get_slugs(),
                             self.question.exam.pk, self.question.pk))

    def get_shorten_text(self):
        return textwrap.shorten(self.explanation_text, 70,
                                placeholder='...')

    def __str__(self):
        if self.question:
            return "Explanation revision #{} of Q#{}".format(self.pk, self.question.pk)
        else:
            return "Explanation revision #{}".format(self.pk)

class Mnemonic(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="mnemonic_images",
                              blank=True)
    text = models.TextField(default="")
    likes = models.ManyToManyField(User, blank=True,
                                   related_name="liked_mnemonic")
    # reports = models.ManyToManyField(User, blank=True,
    #                                         related_name="reported_mnemonic")
    submitter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    objects = managers.MnemonicQuerySet.as_manager()

    target_notifications = GenericRelation('notifications.Notification',
                                           content_type_field='target_content_type',
                                           object_id_field='target_object_id',
                                           related_query_name="target_mnemonics")
    actor_notifications = GenericRelation('notifications.Notification',
                                           content_type_field='actor_content_type',
                                           object_id_field='actor_object_id',
                                           related_query_name="acting_mnemonics")

    def notify_submitter(self, actor):
        title = "Your mnemonic was liked by another Fuduli!"
        user_credit = accounts.utils.get_user_credit(actor)
        description = "Your mnemonic for question #{} was supported by {}".format(self.question.pk,
                                                                                  user_credit)
        notify.send(actor, recipient=self.submitter, target=self,
                    verb='liked', title=title,
                    description=description, style='support')

    def __str__(self):
        if self.question:
            return "Mnemonic #{} of Q#{}".format(self.pk, self.question.pk)
        else:
            return "Mnemonic #{}".format(self.pk)

status_choices = (
    ('PENDING', 'Pending'),
    ('KEPT', 'Kept'),
    ('EDITED', 'Edited'),
    ('DECLINED', 'Declined'),
)


class DuplicateContainer(models.Model):
    primary_question = models.ForeignKey(Question,
                                         on_delete=models.CASCADE,
                                         related_name="primary_duplicates")
    reviser = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    revision_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=status_choices,
                              default="PENDING")
    submission_date = models.DateTimeField(auto_now_add=True)

    def get_questions(self):
        return (Question.objects.filter(pk=self.primary_question.pk) | \
                Question.objects.filter(pk__in=self.duplicate_set.values('question'))).order_by('pk')

    def get_undeleted_questions(self):
        return self.get_questions().undeleted()

    def get_kept_question(self):
        return self.get_questions().filter(is_deleted=False).first()

    def keep(self, question_to_keep):
        questions_to_delete = self.get_questions().exclude(pk=question_to_keep.pk)
        best_revision = question_to_keep.best_revision

        # Merge corrections
        corrections_to_delete = AnswerCorrection.objects\
                                                .filter(choice__question__in=questions_to_delete)\
                                                .select_related('choice')

        for correction in corrections_to_delete:
            choice_text = correction.choice.text
            try:
                choice_to_keep = best_revision.choices.get(text__iexact=choice_text,
                                                           answer_correction__isnull=True)
            except (Choice.DoesNotExist, MultipleObjectsReturned):
                pass
            else:
                correction.choice = choice_to_keep

        # MERGE SESSIONS AND ANSWERS
        # Get all sessions with the question to delete

        # 1) We replace the question field of all skipped answers.
        # 2) We get the alternative choice, replace the choice
        #    field, and replace the question field of all
        #    non-skipped answers.

        # OPTIMIZE: We unpack the primary keys in
        # questions_to_delete_pks and question_to_keep_session_pks
        # before passing them to the QuerySet.  Otherwise, the SQL
        # statement will fail before compilation.  Idealy, there
        # should be a better, SQL-native way to do this.
        questions_to_delete_pks = list(questions_to_delete.values_list('pk', flat=True))
        sessions = Session.objects.filter(questions__in=questions_to_delete_pks).distinct()

        # We will skip changing answers that happen to be in the same
        # session as question_to_keep as this would violate the
        # unique_together constrain in the Answer model.
        question_to_keep_session_pks = list(question_to_keep.session_set.values_list('pk', flat=True))
        obsolete_answers = Answer.objects.filter(question__in=questions_to_delete_pks)\
                                         .exclude(session__in=question_to_keep_session_pks)
        obsolete_answers.update(question=question_to_keep)
        for choice in best_revision.choices.all():
            obsolete_answers.filter(choice__text=choice.text).update(choice=choice)

        for session in sessions:
            session.questions.add(question_to_keep)
            session.questions.remove(*questions_to_delete)

        # MERGE SOURCES
        sources = Source.objects.filter(question__in=questions_to_delete_pks).distinct()
        question_to_keep.sources.add(*sources)

        # MERGE SUBJECTS
        subjects = Subject.objects.filter(question__in=questions_to_delete_pks).distinct()
        question_to_keep.subjects.add(*subjects)

        # MERGE EXAM TYPES
        exam_types = ExamType.objects.filter(question__in=questions_to_delete_pks).distinct()
        question_to_keep.exam_types.add(*exam_types)

        # MERGE MARKING USERS
        marking_users = User.objects.filter(marked_questions__in=questions_to_delete_pks).distinct()
        question_to_keep.marking_users.add(*marking_users)

        questions_to_delete.update(is_deleted=True)

    def __str__(self):
        return "Duplicate container of Q#{} ({} duplicates)".format(self.primary_question.pk,
                                                                    self.duplicate_set.count())

class Duplicate(models.Model):
    container = models.ForeignKey(DuplicateContainer, null=True, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, null=True, on_delete=models.CASCADE,
                                 related_name="secondary_duplicates")
    ratio = models.FloatField()
    objects = managers.DuplicateQuerySet.as_manager()

    def get_percentage(self):
        return round(self.ratio * 100, 2)

    def __str__(self):
        return "Duplicate of Q#{} in container #{}".format(self.question.pk,
                                                           self.container.pk)

    class Meta:
        ordering = ('question',)
        unique_together = ("container", "question")

def validate_regex(value):
    try:
        re.compile(value)
    except re.error:
        raise ValidationError('Please enter a valid regular expression.')

class Rule(models.Model):
    description = models.CharField(max_length=40, blank=True)
    scope_choices = (
        ('ALL', 'Both revisions and changes'),
        ('REVISIONS', 'Revisions'),
        ('CHOICES', 'Choices'),
    )
    scope =  models.CharField(max_length=15, choices=scope_choices,
                              default="ALL")
    # Let's validate the regular expression, but only for the pattern,
    # and not the replacement, which is client-side/JavaScript.
    regex_pattern = models.CharField(max_length=120, validators=[validate_regex])
    regex_replacement = models.CharField(max_length=120, blank=True)
    is_automatic = models.BooleanField(default=False)
    is_disabled = models.BooleanField(default=False)
    priority = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ('priority',)

    def __str__(self):
        return self.description or "'{}' -> '{}'".format(self.regex_pattern,
                                                         self.regex_replacement)

class SuggestedChange(models.Model):
    rules = models.ManyToManyField(Rule, blank=True)
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE)

    status = models.CharField(max_length=20, choices=status_choices,
                              default="PENDING")
    reviser = models.ForeignKey(User, null=True, blank=True,
                                on_delete=models.SET_NULL)
    revision_date = models.DateTimeField(null=True, blank=True)

    submission_date = models.DateTimeField(auto_now_add=True)

    def apply_changes(self, revision_text):
        data = {'text': revision_text,
                'change_summary': 'Automatic edit'}
        if revision.figure:
            file_data = {'figure': revision.figure.file}
        else:
            file_data = {}
        form = RevisionForm(data, file_data, instance=revision)
        form.is_valid()
        form.clone()

    def __str__(self):
        return "Suggested change for Q#%s" % self.revision.question.pk

class SessionTheme(models.Model):
    name = models.CharField(max_length=50)

    primary_background_color = models.CharField(max_length=50, blank=True)
    secondary_background_color = models.CharField(max_length=50, blank=True)
    tertiary_background_color = models.CharField(max_length=50, blank=True)
    tooltip_background_color = models.CharField(max_length=50, blank=True)

    primary_font_color = models.CharField(max_length=50, blank=True)
    secondary_font_color = models.CharField(max_length=50, blank=True)
    tertiary_font_color = models.CharField(max_length=50, blank=True)
    tooltip_font_color = models.CharField(max_length=50, blank=True)

    highlight_background = models.CharField(max_length=50, blank=True)
    highlight_color = models.CharField(max_length=50, blank=True)

    table_active = models.CharField(max_length=50, blank=True)
    table_hover = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name

class Figure(models.Model):
    figure = models.ImageField(upload_to="figures")
    caption = models.TextField(blank=True)

    def __str__(self):
        return self.caption or self.figure.url

class Trigger(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    description = models.CharField(max_length=100, blank=True)
    number_of_questions = models.PositiveIntegerField(null=True,
                                                      blank=True)
    session_mode = models.CharField(max_length=20,
                                    choices=session_mode_choices,
                                    default='UNEXPLAINED')

    def get_number_of_questions(self):
        return self.number_of_questions or \
            self.exam.question_set.approved().count()

    def __str__(self):
        return f"{self.exam.name} ({self.description})"
