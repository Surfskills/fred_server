from django.contrib import admin
from .models import ChatRoom, Message
from django.utils.html import format_html
from django.contrib.contenttypes.models import ContentType

from chat import models


# Inline admin for messages within a chat room
class MessageInline(admin.TabularInline):
    model = Message
    extra = 1
    readonly_fields = ['sender', 'content', 'timestamp', 'is_read', 'read_at']
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        # Disable the option to add messages manually in this inline
        return False

# Admin for the ChatRoom model
@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'admin', 'content_type', 'object_id', 'created_at', 'updated_at', 'is_active', 'message_count')
    list_filter = ('is_active', 'content_type', 'client', 'admin', 'created_at')
    search_fields = ('client__email', 'admin__email', 'object_id')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MessageInline]
    actions = ['mark_as_active', 'mark_as_inactive']

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'

    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} chat rooms have been marked as active.')

    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} chat rooms have been marked as inactive.')

    mark_as_active.short_description = "Mark selected as active"
    mark_as_inactive.short_description = "Mark selected as inactive"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Only show chat rooms for the logged-in admin or for all admins
        if not request.user.is_superuser:
            queryset = queryset.filter(admin=request.user)
        return queryset

    def content_type_display(self, obj):
        # Display human-readable model name
        return f"{obj.content_type.model} ({obj.object_id})"
    content_type_display.short_description = 'Content Type'

# Admin for the Message model
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'sender', 'content', 'timestamp', 'is_read', 'read_at', 'attachment_preview')
    list_filter = ('is_read', 'sender', 'room', 'timestamp')
    search_fields = ('sender__email', 'room__object_id', 'content')
    readonly_fields = ('sender', 'timestamp', 'read_at')
    actions = ['mark_as_read', 'mark_as_unread']

    def attachment_preview(self, obj):
        if obj.attachment:
            return format_html('<a href="{url}" target="_blank">View Attachment</a>', url=obj.attachment.url)
        return '-'
    attachment_preview.short_description = 'Attachment'

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, read_at=models.F('timestamp'))
        self.message_user(request, f'{queryset.count()} messages marked as read.')

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{queryset.count()} messages marked as unread.')

    mark_as_read.short_description = "Mark selected as read"
    mark_as_unread.short_description = "Mark selected as unread"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Only show messages for the logged-in admin or client
        if not request.user.is_superuser:
            queryset = queryset.filter(room__admin=request.user)
        return queryset
