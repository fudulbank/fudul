from django.db import models
from django.db.models import Q, Count
import accounts.utils

class QuestionQuerySet(models.QuerySet):
    def unapproved(self):
        return self.undeleted()\
                   .exclude(revision__is_approved=True)\
                   .distinct()

    def approved(self):
        return self.undeleted()\
                   .filter(revision__is_approved=True,
                           revision__is_deleted=False)\
                   .distinct()

    def unsolved(self):
        return self.filter(~Q(revision__choice__is_right=True),
                           revision__is_deleted=False,
                           revision__is_last=True)\
                   .distinct()

    def incomplete(self):
        return self.filter(~Q(revision__statuses__code_name='COMPLETE'),
                           revision__is_deleted=False,
                           revision__is_last=True)\
                   .distinct()

    def complete(self):
        return self.filter(revision__statuses__code_name='COMPLETE',
                           revision__is_deleted=False,
                           revision__is_last=True)\
                   .distinct()

    def order_global_sequence(self):
        return self.order_by('global_sequence')

    def order_by_submission(self):
        return self.order_by('-pk')

    def undeleted(self):
        return self.filter(is_deleted=False)

class RevisionQuerySet(models.QuerySet):
    def order_by_submission(self):
        return self.order_by('-pk')

    def per_exam(self, exam):
        return self.filter(question__exam=exam).distinct()

    def undeleted(self):
        return self.filter(is_deleted=False,
                           question__is_deleted=False)

class ChoiceQuerySet(models.QuerySet):
    def order_by_alphabet(self):
        return self.order_by('text')

class MetaInformationQuerySet(models.QuerySet):
    def order_by_exam_questions(self, exam):
        return self.filter(question__exam=exam)\
                   .annotate(total_questions=Count('question'))\
                   .order_by('-total_questions')

    def with_approved_questions(self):
        return self.filter(question__is_deleted=False,
                           question__revision__is_approved=True,
                           question__revision__is_deleted=False)\
                   .annotate(Count('question'))\
                   .filter(question__count__gte=1)

class SourceQuerySet(MetaInformationQuerySet):
    def order_by_exam_questions(self, exam):
        # Here, in addition to sorting by total question, we sort
        # alphabetically.
        qs = super(SourceQuerySet, self).order_by_exam_questions(exam)
        return qs.order_by('-total_questions', 'name')

class CategoryQuerySet(models.QuerySet):
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

