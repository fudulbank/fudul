from django.db import models
from django.db.models import Q, Count
import accounts.utils


class QuestionQuerySet(models.QuerySet):
    def unapproved(self):
        return self.undeleted()\
                   .exclude(revision__is_approved=True)\
                   .distinct()

    def used_by_user(self, user):
        return self.filter(answer__session__submitter=user)\
                   .distinct()

    def unused_by_user(self, user):
        return self.exclude(answer__session__submitter=user)\
                   .distinct()

    def correct_by_user(self, user):
        # As a general rule, we will show statistics that are in favor
        # of the user.  For example, if a question has one correct
        # answer, then the user got it (regardless of whether it has
        # other incorrect/skipped answers).
        return self.used_by_user(user)\
                   .filter(answer__choice__is_right=True)\
                   .distinct()

    def incorrect_by_user(self, user):
        # See the note in 'self.correct_by_user()'
        return self.used_by_user(user)\
                   .exclude(answer__choice__is_right=True)\
                   .filter(answer__choice__is_right=False)\
                   .distinct()

    def skipped_by_user(self, user):
        # See the note in 'self.correct_by_user()'
        return self.used_by_user(user)\
                   .exclude(answer__choice__is_right=True)\
                   .exclude(answer__choice__is_right=False)\
                   .filter(answer__choice__isnull=True)\
                   .distinct()

    def approved(self):
        return self.undeleted()\
                   .filter(revision__is_approved=True,
                           revision__is_deleted=False)\
                   .distinct()

    def unsolved(self):
        return self.undeleted()\
                   .filter(~Q(revision__choice__is_right=True),
                           revision__is_deleted=False,
                           revision__is_last=True)\
                   .distinct()

    def incomplete(self):
        return self.undeleted()\
                   .filter(~Q(revision__statuses__code_name='COMPLETE'),
                           revision__is_deleted=False,
                           revision__is_last=True)\
                   .distinct()

    def complete(self):
        return self.undeleted()\
                   .filter(revision__statuses__code_name='COMPLETE',
                           revision__is_deleted=False,
                           revision__is_last=True)\
                   .distinct()

    def order_global_sequence(self):
        return self.order_by('global_sequence')

    def order_by_submission(self):
        return self.order_by('-pk')

    def undeleted(self):
        return self.annotate(revision_count=Count('revision'))\
                   .filter(is_deleted=False)\
                   .exclude(revision_count=0)

class RevisionQuerySet(models.QuerySet):
    def order_by_submission(self):
        return self.order_by('-pk')

    def per_exam(self, exam):
        return self.filter(question__exam=exam).distinct()

    def undeleted(self):
        return self.filter(is_deleted=False,
                           question__is_deleted=False)

class ExamQuerySet(models.QuerySet):
    def with_approved_questions(self):
        return self.filter(question__is_deleted=False,
                           question__revision__is_approved=True,
                           question__revision__is_deleted=False)

class SessionQuerySet(models.QuerySet):
    def with_approved_questions(self):
        return self.filter(questions__is_deleted=False,
                           questions__revision__is_deleted=False,
                           questions__revision__is_approved=True)\
                   .distinct()

    def nonsolved(self):
        return self.exclude(session_mode='SOLVED')

class ChoiceQuerySet(models.QuerySet):
    def order_by_alphabet(self):
        return self.order_by('text')

class MetaInformationQuerySet(models.QuerySet):
    def order_by_exam_questions(self, exam):
        return self.with_approved_questions(exam)\
                   .annotate(total_questions=Count('question'))\
                   .order_by('-total_questions')

    def with_undeleted_questions(self):
        return self.filter(question__is_deleted=False,
                           question__revision__is_deleted=False)

    def with_approved_questions(self, exam=None):
        kwargs = {'question__is_deleted': False,
                  'question__revision__is_deleted': False,
                  'question__revision__is_approved': True}

        if exam:
            kwargs['question__exam'] = exam
        return self.filter(**kwargs).distinct()

class SourceQuerySet(MetaInformationQuerySet):
    def order_by_exam_questions(self, exam):
        # Here, in addition to sorting by total question, we sort
        # alphabetically.
        qs = super(SourceQuerySet, self).order_by_exam_questions(exam)
        return qs.order_by('-total_questions', 'name')

class CategoryQuerySet(models.QuerySet):
    def meta(self):
        return self.filter(Q(exams__isnull=False) | Q(children__isnull=False),
                           parent_category__isnull=True)\
                   .distinct()

    def get_from_slugs(self, slugs):
        slug_list = [slug for slug in slugs.split('/') if slug]
        last_slug = slug_list.pop(-1)
        slug_list.reverse()
        kwargs = {'slug': last_slug}
        level = 'parent_category'
        for slug in slug_list:
            kwarg = level + '__slug'
            kwargs[kwarg] = slug
            level += '__parent_category'
        # Last parent to be a meta tag, with no parents
        kwarg = level + '__isnull'
        kwargs[kwarg] = True

        category = self.filter(**kwargs).first()
        return category

    def user_accessible(self, user):
        if user.is_superuser:
            return self

        user_college = accounts.utils.get_user_college(user)
        if not user_college:
            return self.none()

        pks = []
        for category in self.filter(college_limit__isnull=False):
            if category.college_limit.filter(pk=user_college.pk).exists():
                pks.append(category.pk)

        universally_accessible_categories = self.filter(college_limit__isnull=True)

        return universally_accessible_categories | self.filter(pk__in=pks)

class AnswerQuerySet(models.QuerySet):
    def of_undeleted_questions(self):
        return self.filter(question__is_deleted=False)
