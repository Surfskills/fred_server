from django.contrib import admin
from django.utils.html import format_html

from .models import SupportTicket, Comment, SupportTicketAttachment, ActivityLog

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ['author', 'created_at']

class AttachmentInline(admin.TabularInline):
    model = SupportTicketAttachment
    extra = 0

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        'subject_short',
        'submitted_by',
        'issue_category',
        'status_badge',
        'priority_badge',
        'assigned_to',
        'tenant_scope',
        'created_at',
    )
    list_filter = ('status', 'priority', 'issue_category', 'tenant_kind', 'payment_related', 'technical_issue')
    search_fields = ('subject', 'description', 'affiliate_id', 'submitted_by__email', 'email', 'name')
    inlines = [CommentInline, AttachmentInline]
    readonly_fields = ('submitted_by', 'created_at', 'updated_at')
    list_select_related = ('submitted_by', 'assigned_to')
    date_hierarchy = 'created_at'
    list_per_page = 40
    autocomplete_fields = ('submitted_by', 'assigned_to')
    save_on_top = True
    actions = ['assign_to_me', 'mark_status_in_progress', 'mark_status_resolved', 'mark_status_closed']
    fieldsets = (
        (None, {'fields': ('submitted_by', 'affiliate_id', 'status', 'priority', 'assigned_to')}),
        ('Ticket Details', {'fields': (
            'subject', 'description', 'issue_category',
            'name', 'email',
            'payment_related', 'marketing_materials',
            'commission_dispute', 'technical_issue',
            'affected_customers',
            'tenant_kind', 'tenant_id',
        )}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    def subject_short(self, obj):
        return obj.subject[:80] + '...' if len(obj.subject) > 80 else obj.subject
    subject_short.short_description = 'Subject'
    subject_short.admin_order_field = 'subject'

    def status_badge(self, obj):
        colors = {
            'open': '#2563eb',
            'in_progress': '#ea580c',
            'resolved': '#059669',
            'closed': '#475569',
        }
        color = colors.get(obj.status, '#475569')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def priority_badge(self, obj):
        colors = {
            'low': '#16a34a',
            'medium': '#ca8a04',
            'high': '#ea580c',
            'critical': '#b91c1c',
        }
        color = colors.get(obj.priority, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;">{}</span>',
            color,
            obj.get_priority_display(),
        )
    priority_badge.short_description = 'Priority'
    priority_badge.admin_order_field = 'priority'

    def tenant_scope(self, obj):
        if obj.tenant_kind and obj.tenant_id:
            return f"{obj.tenant_kind}:{obj.tenant_id}"
        return obj.tenant_kind or 'personal'
    tenant_scope.short_description = 'Tenant'

    def assign_to_me(self, request, queryset):
        updated = queryset.update(assigned_to=request.user)
        self.message_user(request, f'{updated} tickets assigned to you.')
    assign_to_me.short_description = 'Assign selected tickets to me'

    def mark_status_in_progress(self, request, queryset):
        updated = queryset.exclude(status='closed').update(status='in_progress')
        self.message_user(request, f'{updated} tickets moved to in progress.')
    mark_status_in_progress.short_description = 'Mark selected as in progress'

    def mark_status_resolved(self, request, queryset):
        updated = queryset.exclude(status='closed').update(status='resolved')
        self.message_user(request, f'{updated} tickets marked resolved.')
    mark_status_resolved.short_description = 'Mark selected as resolved'

    def mark_status_closed(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f'{updated} tickets closed.')
    mark_status_closed.short_description = 'Close selected tickets'

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'content_preview', 'created_at')
    search_fields = ('content', 'author__email', 'ticket__subject')
    list_select_related = ('ticket', 'author')
    date_hierarchy = 'created_at'

    def content_preview(self, obj):
        return obj.content[:90] + '...' if len(obj.content) > 90 else obj.content
    content_preview.short_description = 'Comment'

@admin.register(SupportTicketAttachment)
class SupportTicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'file', 'uploaded_at')
    search_fields = ('ticket__subject',)
    list_select_related = ('ticket',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'activity_type', 'performed_by', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('ticket__subject', 'description', 'performed_by__email')
    readonly_fields = ('ticket', 'activity_type', 'description', 'performed_by', 'created_at', 'metadata')
    list_select_related = ('ticket', 'performed_by')
    date_hierarchy = 'created_at'