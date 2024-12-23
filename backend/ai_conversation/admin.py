from django.contrib import admin

from .models import AiConversationLimit, AiConversation

# Register your models here.
class AiConversationLimitAdmin(admin.ModelAdmin):
    model = AiConversationLimit
    list_display = ['user', 'limit', 'timestamp', 'updated']

admin.site.register(AiConversationLimit, AiConversationLimitAdmin)


class AiConversationAdmin(admin.ModelAdmin):
    model = AiConversation
    list_display = ['user', 'conversation_start', 'conversation_end', 'status', 'conversation_type', 'app', 'developer']

admin.site.register(AiConversation, AiConversationAdmin)