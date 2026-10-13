from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'message')
    date_hierarchy = 'created_at'
    autocomplete_fields = ('user',)
