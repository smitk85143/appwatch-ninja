from django.contrib import admin
from home.models import AppDetail, Developer, Genre, Store, CountryCode

class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
    
class ChangeOnlyAdmin(admin.ModelAdmin):

    def has_change_permission(self, request, obj=None):
        return True

class CountryCodeAdmin(ReadOnlyAdmin):
    search_fields = ['name', 'code']
    list_display = ['name', 'code']

admin.site.register(CountryCode, CountryCodeAdmin)

class GenreAdmin(ReadOnlyAdmin):
    search_fields = ['genreId', 'genre']
    list_display = ['genreId', 'genre']

admin.site.register(Genre, GenreAdmin)

class DeveloperAdmin(ChangeOnlyAdmin):
    search_fields = ['developerId','sellerName','slug']
    list_display = ['sellerName', 'developerId']

admin.site.register(Developer, DeveloperAdmin)

class AppDetailAppsAdmin(ChangeOnlyAdmin):
    search_fields = ['appID', 'name', 'developer__sellerName']
    list_display = ['name', 'appID', 'developer', 'userAvgRating', 'ratings', 'free']

admin.site.register(AppDetail, AppDetailAppsAdmin)

class StoreAdmin(ReadOnlyAdmin):
    list_display = ['name']

admin.site.register(Store, StoreAdmin)