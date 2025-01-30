from django.contrib import admin
from .models import UserDesireApp, UserWatchlist, ASORequest, ASOGoal

class UserDesireAppAdmin(admin.ModelAdmin):
    list_display = ['user', 'appID', 'store', 'added']
    search_fields = ['appID', 'user__email']

admin.site.register(UserDesireApp, UserDesireAppAdmin)

class UserWatchlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'app', 'added']

admin.site.register(UserWatchlist, UserWatchlistAdmin)

class ASORequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization_name', 'approved']
    search_fields = ['user__email']

admin.site.register(ASORequest, ASORequestAdmin)

class ASOGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

admin.site.register(ASOGoal, ASOGoalAdmin)
