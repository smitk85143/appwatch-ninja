from django.contrib import admin
from .models import CustomUser

admin.site.site_header = 'App Analytics Administration'
admin.site.index_title = 'My Administration'
admin.site.site_title = 'Site adminsitration'

class CustomUserAdmin(admin.ModelAdmin):
    model = CustomUser
    list_display = ['email', 'is_staff', 'is_user_verified', 'subscription_type']

admin.site.register(CustomUser, CustomUserAdmin)