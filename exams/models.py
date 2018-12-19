from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
import datetime
import textwrap
import re

from . import managers
from accounts.models import College, Batch
from ckeditor_uploader.fields import RichTextUploadingField
from notifications.models import Notification
from notifications.signals import notify
import accounts.utils


class Source(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey('Category')
    parent_source = models.ForeignKey('self', null=True, blank=True,
                                      related_name="children",
                                      on_delete=models.SET_NULL)
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
    college_limit = models.ManyToManyField(College, blank=True)
    parent_category = models.ForeignKey('self', null=True, blank=True,
                                        related_name="children",
                                        on_delete=models.SET_NULL,
                                        default=None)
    is_listed = models.BooleanField("This category is listed upon showing categories and on the sidebar",
                                    default=True, blank=True)
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
        if not user.is_authenticated():
            return False
        elif user.is_superuser:
            return True

        user_college = accounts.utils.get_user_college(user)
        category = self

        while category:
            if category.college_limit.exists() and \
               (not user_college or \
                not category.college_limit.filter(pk=user_college.pk).exists()):
                return False
            category = category.parent_category

        return True

    def get_slugs(self):
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
    category = models.ForeignKey(Category,related_name='exams')
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    batches_allowed_to_take = models.ForeignKey(Batch, null=True, blank=True)
    exam_types = models.ManyToManyField('ExamType', blank=True)
    credits = RichTextUploadingField(default='', blank=True)
    was_announced = models.BooleanField("This exam was announced and is readily available for users who are not editors",
                                        default=True, blank=True)

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
        return User.objects.filter(session__exam=self)\
                           .distinct()\
                           .count()
    get_user_count.short_description = '# users'

    def get_sources(self):
        sources = Source.objects.none()
        category = self.category
        while category:
            sources |= category.source_set.all()
            category = category.parent_category
        return sources

    def get_editors(self):
        members = User.objects.filter(team_memberships__exams=self)
        return members

    def can_user_access(self, user):
        return self.category.can_user_access(user)

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
    exam = models.ForeignKey(Exam, related_name='exam_dates')
    batch = models.ForeignKey('accounts.Batch',
                              related_name='exam_dates')
    date = models.DateField()

    def __str__(self):
        data_str = self.date.strftime('%Y-%m-%d')
        return "{} on {}".format(self.name, data_str)

class Subject(models.Model):
    name = models.CharField(max_length=100)
    exam = models.ForeignKey(Exam)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    objects = managers.MetaInformationQuerySet.as_manager()

    def get_selector(self):
        return 's-' + str(self.pk)

    def __str__(self):
        return self.name

class Question(models.Model):
    sources = models.ManyToManyField(Source, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True)
    exam = models.ForeignKey(Exam)
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
    assigned_editor = models.ForeignKey(User, null=True, blank=True,
                                        on_delete=models.SET_NULL,
                                        related_name="assigned_questions")

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
        user_pks = Answer.objects.filter(choice__revision__question=self)\
                                 .values('session__submitter')
        return User.objects.filter(pk__in=user_pks)\
                           .count()

    def update_best_revision(self):
        best_revision = self.get_best_revision()
        self.best_revision = best_revision

    def update_is_approved(self):
        approved_revision = self.get_latest_approved_revision()
        if approved_revision and \
           not self.is_deleted and \
           not self.issues.filter(is_blocker=True).exists() and \
           approved_revision.choice_set.filter(is_right=True).exists() and \
           approved_revision.choice_set.count() > 1:
            self.is_approved = True
        else:
            self.is_approved = False

    def update_latest(self):
        latest_revision = self.get_latest_revision()
        if latest_revision:
            self.revision_set.exclude(pk=latest_revision.pk)\
                             .update(is_last=False)
            if not latest_revision.is_last:
                latest_revision.is_last = True
                latest_revision.save()

        latest_explanation_revision = self.get_latest_explanation_revision()
        if latest_explanation_revision:
            self.explanation_revisions.exclude(pk=latest_explanation_revision.pk)\
                                      .update(is_last=False)
            if not latest_explanation_revision.is_last:
                latest_explanation_revision.is_last = True
                latest_explanation_revision.save()

    def is_incomplete(self):
        latest_revision = self.get_latest_revision()
        if self.issues.filter(is_blocker=True).exists() or \
           not latest_revision.choice_set.filter(is_right=True).exists() or \
           latest_revision.choice_set.count >= 1:
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

    def get_correct_others(self):
        correct_user_pks = Answer.objects.filter(question=self,
                                                 choice__is_right=True)\
                                         .values_list('session__submitter', flat=True)
        total_user_pks = Answer.objects.filter(question=self)\
                                       .values_list('session__submitter', flat=True)
        correct_users = User.objects.filter(pk__in=correct_user_pks).count()
        total_users = User.objects.filter(pk__in=total_user_pks).count()
        result = correct_users / total_users * 100
        return round(result, 1)

    def get_contributors(self):
        contributors = []
        for revision in self.revision_set.select_related('submitter',
                                                         'submitter__profile')\
                                         .undeleted()\
                                         .order_by('pk'):
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

    def get_available_mnemonics(self):
        return self.mnemonic_set.filter(is_deleted=False)

class Revision(models.Model):
    question = models.ForeignKey(Question)
    submitter = models.ForeignKey(User, null=True, blank=True)
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
    approved_by = models.ForeignKey(User,related_name="approved_revision",null=True, blank=True)

    target_notifications = GenericRelation('notifications.Notification',
                                           content_type_field='target_content_type',
                                           object_id_field='target_object_id',
                                           related_query_name="target_revisions")
    actor_notifications = GenericRelation('notifications.Notification',
                                           content_type_field='actor_content_type',
                                           object_id_field='actor_object_id',
                                           related_query_name="acting_revisions")

    def get_previous(self):
        return self.question.revision_set\
                            .filter(is_deleted=False,
                                    submission_date__lt=self.submission_date)\
                            .order_by('submission_date').last()

    def get_right_choice(self):
        return self.choice_set.filter(is_right=True).first()

    def has_right_answer(self):
        return self.choice_set.filter(is_right=True).exists()

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
    session_mode = models.CharField(max_length=20, choices=session_mode_choices, default=None)
    parent_session = models.ForeignKey('self',
                                       related_name="children",
                                       null=True,
                                       blank=True)
    secret_key = models.CharField(max_length=10)
    number_of_questions = models.PositiveIntegerField(null=True)
    sources = models.ManyToManyField(Source, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True)
    exam = models.ForeignKey(Exam)
    questions = models.ManyToManyField(Question, blank=True)
    exam_types = models.ManyToManyField(ExamType, blank=True)
    submitter = models.ForeignKey(User)
    question_filter = models.CharField(max_length=20, choices=questions_choices, default=None)
    submission_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    is_automatic = models.BooleanField(default=False)
    actor_notifications = GenericRelation('notifications.Notification',
                                          content_type_field='actor_content_type',
                                          object_id_field='actor_object_id',
                                          related_query_name="sessions")

    # We store this value instead of calculating it dynamically,
    # because this can tremendously enhance performance.  This only
    # applies to sessions that have the exam mode enabled (does not
    # apply to session.session_mode = 'SOLVED' and
    # session.session_mode = 'INCOMPLETE')
    has_finished = models.NullBooleanField(default=None)

    objects = managers.SessionQuerySet.as_manager()

    def get_skipped_count(self):
        question_pool = self.get_questions()
        return question_pool.filter(answer__choice__isnull=True,
                                    answer__session=self)\
                            .count() or 0

    def get_correct_count(self):
        question_pool = self.get_questions()
        return question_pool.filter(answer__choice__is_right=True,
                                    answer__session=self)\
                            .count() or 0

    def get_incorrect_count(self):
        question_pool = self.get_questions()
        return question_pool.filter(answer__choice__is_right=False,
                                    answer__session=self)\
                            .count() or 0

    def get_score(self):
        try:
            total = self.get_questions().count()
            correct = self.get_correct_count()
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

    def get_used_questions_count(self):
        return self.answer_set.of_undeleted_questions()\
                              .distinct()\
                              .count()

    def is_examinable(self):
        return self.session_mode not in ['INCOMPLETE', 'SOLVED']

    def set_has_finished(self):
        # Session that are either 'INCOMPLETE' or 'SOLVED' cannot be
        # considered 'finsihed'
        if not self.is_examinable():
            return

        has_finished = not self.get_unused_questions().exists()

        # Do not trigger save, unless the value has changed
        if self.has_finished != has_finished:
            self.has_finished = has_finished
            self.save()

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
        # If a question PK is given, show it.  Otheriwse show the first
        # session unused question.  Otherwise, show the first session
        # question.
        if question_pk:
            current_question = get_object_or_404(self.get_questions(), pk=question_pk)
        elif not self.has_finished:
            current_question = self.get_unused_questions().first()
        else:
            current_question = self.get_questions()\
                                   .order_by('global_sequence')\
                                   .first()

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
    session = models.ForeignKey(Session)
    question = models.ForeignKey(Question)
    choice = models.ForeignKey(Choice, null=True)

    submission_date = models.DateTimeField(auto_now_add=True, null=True)

    objects = managers.AnswerQuerySet.as_manager()

    class Meta:
        unique_together = ("session", "question")

    def __str__(self):
        return "Answer of Q#{} in S#{}".format(self.question.pk,
                                               self.session.pk)

class Highlight(models.Model):
    session = models.ForeignKey(Session)
    question = models.ForeignKey(Question, null=True)

    # Since revision text and choices are changeable, but we also want
    # to keep the highlights/strikes, let's remember which revision
    # was the user faced with.  In case the text of that revision and
    # the showed revision differs, we won't keep
    revision = models.ForeignKey(Revision)
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
                                  related_name="answer_correction")
    supporting_users = models.ManyToManyField(User, blank=True,
                                              related_name="supported_corrections")
    opposing_users = models.ManyToManyField(User, blank=True,
                                            related_name="opposed_corrections")
    submitter = models.ForeignKey(User)
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
        description = "Your correction for question #{} was supported by {}".format(self.choice.revision.question.pk,
                                                                                    user_credit)
        notify.send(actor, recipient=self.submitter, target=self,
                    verb='supported', title=title,
                    description=description, style='support')

    def can_user_delete(self, user):
        return self.submitter == user or \
               self.choice.revision.question.exam.can_user_edit(user)

    def __str__(self):
        return "Correction of Q#{}".format(self.choice.revision.question.pk)

class ExplanationRevision(models.Model):
    question = models.ForeignKey(Question,
                                 related_name="explanation_revisions")
    submitter = models.ForeignKey(User, null=True, blank=True,
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
    question = models.ForeignKey(Question)
    image = models.ImageField(upload_to="mnemonic_images",
                              blank=True)
    text = models.TextField(default="")
    likes = models.ManyToManyField(User, blank=True,
                                   related_name="liked_mnemonic")
    # reports = models.ManyToManyField(User, blank=True,
    #                                         related_name="reported_mnemonic")
    submitter = models.ForeignKey(User)
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
                                         related_name="primary_duplicates")
    reviser = models.ForeignKey(User, null=True, blank=True)
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
                                                .filter(choice__revision__question__in=questions_to_delete)\
                                                .select_related('choice')

        for correction in corrections_to_delete:
            choice_text = correction.choice.text
            try:
                choice_to_keep = best_revision.choice_set.get(text__iexact=choice_text,
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

        # Construct an easy-to-access choice dictionary to
        # save repeated database queries
        choices_to_keep = {}
        for choice in best_revision.choice_set.all():
            choices_to_keep[choice.text] = choice

        sessions = Session.objects.filter(questions__in=questions_to_delete).distinct()

        for session in sessions:
            session.questions.add(question_to_keep)
            session.questions.remove(*questions_to_delete)
            obsolete_answers = session.answer_set.select_related('choice')\
                                                 .filter(question__in=questions_to_delete)
            if not session.answer_set.filter(question=question_to_keep).exists() and \
               obsolete_answers.exists():
                # For each session, we will look for an obsolete
                # answers that either has the same choice text, or was
                # skipped.  If all that exist are obsolete answers
                # with text that are different, ignore it.
                answer_to_change = obsolete_answers.filter(choice__text__in=best_revision.choice_set.values('text'))\
                                                   .distinct()\
                                                   .first() or \
                                   obsolete_answers.filter(choice__isnull=True)\
                                                   .first()
                if answer_to_change:
                    # If the choice is not null, replace it with a
                    # choice that has the same text.
                    if answer_to_change.choice:
                        choice = choices_to_keep[answer_to_change.choice.text]
                        answer_to_change.choice = choice
                    answer_to_change.question = question_to_keep
                    answer_to_change.save()

        # MERGE THE SOURCES
        for source in Source.objects.filter(question__in=questions_to_delete).distinct():
            question_to_keep.sources.add(source)

        # MERGE THE SUBJECT
        for subject in Subject.objects.filter(question__in=questions_to_delete).distinct():
            question_to_keep.subjects.add(subject)

        # MERGE THE SUBJECT
        for exam_type in ExamType.objects.filter(question__in=questions_to_delete).distinct():
            question_to_keep.exam_types.add(exam_type)

        # MERGE MARKING USERS
        question_to_keep.marking_users.add(*User.objects.filter(marked_questions__in=questions_to_delete).distinct())

        questions_to_delete.update(is_deleted=True)

    def __str__(self):
        return "Duplicate container of Q#{} ({} duplicates)".format(self.primary_question.pk,
                                                                    self.duplicate_set.count())

class Duplicate(models.Model):
    container = models.ForeignKey(DuplicateContainer, null=True)
    question = models.ForeignKey(Question, null=True,
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
    revision = models.ForeignKey(Revision)

    status = models.CharField(max_length=20, choices=status_choices,
                              default="PENDING")
    reviser = models.ForeignKey(User, null=True, blank=True)
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
