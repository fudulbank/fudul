from django.db import models
from django.db.models import Q, Count
from django.http import Http404
import accounts.utils
from . import utils
from itertools import chain

class QuestionQuerySet(models.QuerySet):
    def unapproved(self):
        return self.undeleted()\
                   .exclude(revision__is_approved=True)\
                   .distinct()

    def used_by_user(self, user, exclude_skipped=True):
        kwargs = {'answer__session__submitter': user,
                  'answer__session__is_deleted': False}
        if exclude_skipped:
            kwargs['answer__choice__isnull'] = False
        return self.filter(**kwargs)\
                   .distinct()

    def unused_by_user(self, user, exclude_skipped=True):

        kwargs = {'answer__session__submitter': user,
                  'answer__session__is_deleted': False}
        if exclude_skipped:
            kwargs['answer__choice__isnull'] = False

        # We have to do this funny queryset to account for
        # session.is_deleted.  Otherwise, it won't be considered.
        excluded_pks = self.filter(**kwargs).values_list('pk')

        return self.exclude(pk__in=excluded_pks)\
                   .distinct()

    def correct_by_user(self, user):
        # As a general rule, we will show statistics that are in favor
        # of the user.  For example, if a question has one correct
        # answer, then the user got it (regardless of whether it has
        # other incorrect/skipped answers).
        return self.filter(answer__choice__is_right=True,
                           answer__session__is_deleted=False,
                           answer__session__submitter=user)\
                   .distinct()

    def incorrect_by_user(self, user):
        # See the note in 'self.correct_by_user()'
        excluded_pks = self.filter(answer__choice__is_right=True,
                                   answer__session__is_deleted=False,
                                   answer__session__submitter=user)\
                       .values_list('pk')

        return self.exclude(pk__in=excluded_pks)\
                   .filter(answer__choice__is_right=False,
                           answer__session__is_deleted=False,
                           answer__session__submitter=user)\
                   .distinct()

    def skipped_by_user(self, user):
        # See the note in 'self.correct_by_user()'
        excluded_pks = (self.filter(answer__choice__is_right=True,
                                    answer__session__is_deleted=False,
                                    answer__session__submitter=user) |
                        self.filter(answer__choice__is_right=False,
                                    answer__session__is_deleted=False,
                                    answer__session__submitter=user))\
                       .values_list('pk')

        return self.exclude(pk__in=excluded_pks)\
                   .filter(answer__choice__isnull=True,
                           answer__session__is_deleted=False,
                           answer__session__submitter=user)\
                   .distinct()

    def approved(self):
        # Changes here should be reflected in available() and reverted
        # in incomplete
        return self.undeleted()\
                   .without_blocking_issues()\
                   .has_examinable_choices()\
                   .solved()\
                   .filter(revision__is_approved=True,
                           revision__is_deleted=False)\
                   .distinct()

    def solved(self):
        return self.undeleted()\
                   .filter(revision__choice__is_right=True,
                           revision__is_deleted=False,
                           revision__is_last=True)\
                   .distinct()
    
    def unsolved(self):
        return self.undeleted()\
                   .filter(~Q(revision__choice__is_right=True),
                           revision__is_deleted=False,
                           revision__is_last=True)\
                   .distinct()

    def has_examinable_choices(self):
        return self.undeleted()\
                   .filter(revision__is_deleted=False,
                           revision__is_last=True)\
                   .annotate(choice_count=Count('revision__choice'))\
                   .filter(choice_count__gt=1)\
                   .distinct()

    def lacking_choices(self):
        return self.undeleted()\
                   .filter(revision__is_deleted=False,
                           revision__is_last=True)\
                   .annotate(choice_count=Count('revision__choice'))\
                   .filter(choice_count__lte=1)\
                   .distinct()

    def with_issues(self):
        return self.undeleted()\
                   .filter(issues__isnull=False)\
                   .distinct()

    def with_nonblocking_issues(self):
        # If the question has a blocking issue, do not show it here,
        # even if it has a non-blocking issue.  Let's kill overlap.
        return self.undeleted()\
                   .filter(issues__isnull=False)\
                   .exclude(issues__is_blocker=True)\
                   .distinct()

    def with_blocking_issues(self):
        return self.undeleted()\
                   .filter(issues__is_blocker=True)\
                   .distinct()

    def without_blocking_issues(self):
        return self.undeleted()\
                   .exclude(issues__is_blocker=True)\
                   .distinct()

    def with_no_issues(self):
        return self.undeleted()\
                   .filter(issues__isnull=True)\
                   .distinct()

    def with_approved_latest_revision(self):
        return self.undeleted()\
                   .filter(revision__is_last=True,
                           revision__is_approved=True)\
                   .distinct()

    def with_pending_latest_revision(self):
        return self.undeleted()\
                   .filter(revision__is_last=True,
                           revision__is_approved=False)\
                   .distinct()

    def order_global_sequence(self):
        return self.order_by('global_sequence')

    def order_by_submission(self):
        return self.order_by('-pk')

    def undeleted(self):
        return self.filter(is_deleted=False)

    def marked_by_user(self,user):
        return self.undeleted()\
                   .filter(marking_users=user)

    def available(self):
        # We use a a query similar to approved(), but without the
        # unneeded queries (solved, without blocking issues)
        approved = self.undeleted()\
                       .filter(revision__is_approved=True,
                               revision__is_deleted=False)\
                       .distinct()

        return self.with_blocking_issues() | \
               self.unsolved() | \
               self.lacking_choices() | \
               approved

    def incomplete(self):
        # Any added filter should be reverted in approved()
        return self.with_blocking_issues() | \
               self.unsolved() | \
               self.lacking_choices()

    def under_categories(self, categories):
        deepest_category_level = utils.get_deepest_category_level()
        queries = Q()
        for category in categories:
            count = 1
            level = 'exam__category'
            while deepest_category_level >= count:
                kwarg = {level: category}
                level +=  '__parent_category'
                queries |= Q(**kwarg)
                count += 1
        return self.filter(queries)

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
                           question__revision__is_deleted=False)\
                   .distinct()

class SessionQuerySet(models.QuerySet):
    def nonsolved(self):
        return self.exclude(session_mode='SOLVED')

    def undeleted(self):
        return self.filter(is_deleted=False)

class ChoiceQuerySet(models.QuerySet):
    def order_by_alphabet(self):
        return self.order_by('text')

    def order_randomly(self):
        return self.order_by('?')

class MetaInformationQuerySet(models.QuerySet):
    def order_by_exam_questions(self, exam):
        return self.with_approved_questions(exam)\
                   .annotate(total_questions=Count('question'))\
                   .order_by('-total_questions')

    def with_undeleted_questions(self):
        return self.filter(question__is_deleted=False,
                           question__revision__is_deleted=False)\
                   .distinct()

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

    def get_from_slugs_or_404(self, slugs):
        category = self.get_from_slugs(slugs)
        if category:
            return category
        else:
            raise Http404

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
    def correct(self):
        return self.filter(choice__is_right=True)

    def incorrect(self):
        return self.filter(choice__is_right=False)

    def skipped(self):
        return self.filter(choice__isnull=True)

    def of_undeleted_questions(self):
        return self.filter(question__is_deleted=False)

class MnemonicQuerySet(models.QuerySet):
    def undeleted(self,question):
        self.filter(question=question,is_deleted=False)
