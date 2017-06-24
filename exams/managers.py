from django.db import models
import accounts.utils

class QuestionQuerySet(models.QuerySet):
    def unapproved(self):
        return self.undeleted().exclude(revision__is_approved=True)\
                   .distinct()

    def order_by_submission(self):
        return self.order_by('-pk')

    def undeleted(self):
        return self.filter(is_deleted=False)

class RevisionQuerySet(models.QuerySet):
    def order_by_submission(self):
        return self.order_by('-pk')

    def undeleted(self):
        return self.filter(is_deleted=False)

class ChoiceQuerySet(models.QuerySet):
    def order_by_alphabet(self):
        return self.order_by('text')

class SubjectQuerySet(models.QuerySet):
    def order_by_total_questions(self):
        return self.annotate(total_questions=models.Count('question')).order_by('-total_questions')

class SourceQuerySet(models.QuerySet):
    def order_by_total_questions(self):
        return self.annotate(total_questions=models.Count('question')).order_by('-total_questions')

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

