from django.db import models
from django.contrib.auth import get_user_model

from home.models import AppDetail, Developer

class AiConversationLimit(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    limit = models.IntegerField(default=10)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.limit}"


class ConversationType(models.TextChoices):
    NORMAL = "normal", "Normal"
    APP = "app", "App"
    DEVELOPER = "developer", "Developer"


class AiResponseStatus(models.TextChoices):
    ONGOING = "ongoing", "Ongoing"
    COMPLETED = "completed", "Completed"


class AiConversation(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    conversation_start = models.DateTimeField(auto_now_add=True)
    conversation_end = models.DateTimeField(null=True, blank=True)
    conversation_data = models.JSONField(default=list)
    status = models.CharField(
        max_length=20,
        choices=AiResponseStatus.choices,
        default=AiResponseStatus.ONGOING
    )
    conversation_type = models.CharField(
        max_length=20,
        choices=ConversationType.choices,
        default=ConversationType.NORMAL
    )
    app = models.ForeignKey(AppDetail, on_delete=models.SET_NULL, null=True, blank=True)
    developer = models.ForeignKey(Developer, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Conversation {self.id} - {self.user.email} ({self.status})"