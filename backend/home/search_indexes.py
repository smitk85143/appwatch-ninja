from haystack import indexes
from .models import AppDetail
from whoosh.analysis import StandardAnalyzer

class AndroidGooglePlayAppIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', analyzer=StandardAnalyzer(), null=True, stored=True)
    name_ngram = indexes.EdgeNgramField(model_attr='name', null=True, stored=True)
    appID = indexes.CharField(model_attr='appID')
    icon = indexes.CharField(model_attr='icon', null=True)
    store = indexes.CharField(model_attr='store')
    hide = indexes.BooleanField(model_attr='hide')

    def get_model(self):
        return AppDetail

    def index_queryset(self, using=None):
        return self.get_model().objects.all()