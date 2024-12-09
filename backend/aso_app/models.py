from django.db import models
from django.utils import timezone

class Keyword(models.Model):
    keyword = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    def update_synced(self):
        self.last_synced = timezone.now()
        self.save()