from haystack import indexes
from .models import *


class RevisionIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    submission_date = indexes.DateTimeField(model_attr='submission_date')

    def get_model(self):
        return Revision

    def index_queryset(self, using=None):
        return self.get_model().objects.undeleted().filter(is_last=True)
