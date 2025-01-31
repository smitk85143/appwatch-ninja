from haystack import indexes
from whoosh.analysis import StandardAnalyzer
from meilisearch import Client
from django.conf import settings

from .models import AppDetail

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


class SearchIndex:
    index = None

    class Indexes:
        """Available indexes"""
        app = "appdetails"

    def __init__(self, index=None):
        self.index = index or self.Indexes.app

    def get_index(self):
        """Retrieve index"""
        client = Client(settings.MEILISEARCH_URL, settings.MEILISEARCH_KEY)
        return client.index(self.index)

    def delete_doc(self, doc):
        self.get_index().delete_document(doc)

    def clear_index(self):
        self.get_index().delete_all_documents()