from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .models import Payout, PayoutTimeline, PayoutSetting, Earnings


class PayoutTimelineInline(admin.TabularInline):
    model = PayoutTimeline
    extra = 0
    readonly_fields = ('timestamp', 'status', 'changed_by', 'note')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class EarningsInline(admin.TabularInline):
    model = Earnings
    extra = 0
    readonly_fields = ('partner', 'amount', 'status', 'source', 'date', 'view_earning_link')  # Include here
    fields = ('partner', 'amount', 'status', 'source', 'date', 'view_earning_link')  # And here
    can_delete = False

    def view_earning_link(self, obj):
        if obj.id:
            url = reverse('admin:payouts_earning_change', args=[obj.id])
            return format_html('<a href="{}">View Earning</a>', url)
        return "-"
    view_earning_link.short_description = "Action"

    def has_add_permission(self, request, obj=None):
        return False



@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'partner_link', 
        'amount', 
        'status', 
        'payment_method', 
        'request_date', 
        'processed_date',
        'actions_column'
    )
    list_filter = ('status', 'payment_method', 'request_date')
    search_fields = ('id', 'partner__name', 'transaction_id')
    readonly_fields = ('id', 'request_date', 'processed_date', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('id', 'partner', 'requested_by', 'amount', 'status')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'payment_details', 'transaction_id')
        }),
        ('Dates', {
            'fields': ('request_date', 'processed_date', 'updated_at')
        }),
        ('Notes', {
            'fields': ('note', 'client_notes')
        }),
    )
    inlines = [PayoutTimelineInline, EarningsInline]
    actions = ['process_payouts', 'complete_payouts', 'cancel_payouts']

    def partner_link(self, obj):
        if obj.partner:
            url = reverse('admin:authentication_profile_change', args=[obj.partner.id])
            return format_html('<a href="{}">{}</a>', url, obj.partner.name)
        return "-"
    partner_link.short_description = "Partner"
    partner_link.admin_order_field = 'partner__name'

    def actions_column(self, obj):
        links = []
        if obj.can_process:
            url = reverse('admin:payout_payout_process', args=[obj.id])
            links.append(f'<a href="{url}">Process</a>')
        if obj.can_complete:
            url = reverse('admin:payout_payout_complete', args=[obj.id])
            links.append(f'<a href="{url}">Complete</a>')
        if obj.can_cancel:
            url = reverse('admin:payout_payout_cancel', args=[obj.id])
            links.append(f'<a href="{url}">Cancel</a>')
        return format_html(' | '.join(links)) if links else "-"
    actions_column.short_description = "Actions"
    actions_column.allow_tags = True

    def process_payouts(self, request, queryset):
        for payout in queryset.filter(status=Payout.Status.PENDING):
            payout.process(request.user)
        self.message_user(request, f"Processed {queryset.count()} payouts")
    process_payouts.short_description = "Mark selected payouts as processing"

    def complete_payouts(self, request, queryset):
        for payout in queryset.filter(status=Payout.Status.PROCESSING):
            payout.complete(user=request.user)
        self.message_user(request, f"Completed {queryset.count()} payouts")
    complete_payouts.short_description = "Mark selected payouts as completed"

    def cancel_payouts(self, request, queryset):
        for payout in queryset.filter(status__in=[Payout.Status.PENDING, Payout.Status.PROCESSING]):
            payout.cancel(user=request.user)
        self.message_user(request, f"Cancelled {queryset.count()} payouts")
    cancel_payouts.short_description = "Cancel selected payouts"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/process/',
                 self.admin_site.admin_view(self.process_payout),
                 name='payout_payout_process'),
            path('<path:object_id>/complete/',
                 self.admin_site.admin_view(self.complete_payout),
                 name='payout_payout_complete'),
            path('<path:object_id>/cancel/',
                 self.admin_site.admin_view(self.cancel_payout),
                 name='payout_payout_cancel'),
        ]
        return custom_urls + urls

    def process_payout(self, request, object_id, *args, **kwargs):
        from django.shortcuts import redirect
        payout = Payout.objects.get(id=object_id)
        payout.process(request.user)
        self.message_user(request, f"Payout {payout.id} is now processing")
        return redirect(reverse('admin:payouts_payout_change', args=[object_id]))

    def complete_payout(self, request, object_id, *args, **kwargs):
        from django.shortcuts import redirect
        payout = Payout.objects.get(id=object_id)
        payout.complete(user=request.user)
        self.message_user(request, f"Payout {payout.id} completed successfully")
        return redirect(reverse('admin:payouts_payout_change', args=[object_id]))

    def cancel_payout(self, request, object_id, *args, **kwargs):
        from django.shortcuts import redirect
        payout = Payout.objects.get(id=object_id)
        payout.cancel(user=request.user)
        self.message_user(request, f"Payout {payout.id} has been cancelled")
        return redirect(reverse('admin:payouts_payout_change', args=[object_id]))


@admin.register(PayoutTimeline)
class PayoutTimelineAdmin(admin.ModelAdmin):
    list_display = ('payout_link', 'status', 'timestamp', 'changed_by')
    list_filter = ('status', 'timestamp')
    search_fields = ('payout__id', 'changed_by__email')
    readonly_fields = ('payout', 'status', 'timestamp', 'changed_by', 'note')

    def payout_link(self, obj):
        url = reverse('admin:payouts_payout_change', args=[obj.payout.id])
        return format_html('<a href="{}">{}</a>', url, obj.payout.id)
    payout_link.short_description = "Payout"
    payout_link.admin_order_field = 'payout__id'


@admin.register(PayoutSetting)
class PayoutSettingAdmin(admin.ModelAdmin):
    list_display = ('partner_link', 'payment_method', 'minimum_payout_amount', 'auto_payout', 'payout_schedule')
    list_filter = ('payment_method', 'auto_payout', 'payout_schedule')
    search_fields = ('partner__name',)
    readonly_fields = ('updated_at',)

    def partner_link(self, obj):
        url = reverse('admin:authentication_profile_change', args=[obj.partner.id])
        return format_html('<a href="{}">{}</a>', url, obj.partner.name)
    partner_link.short_description = "Partner"
    partner_link.admin_order_field = 'partner__name'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('partner',)
        return self.readonly_fields


@admin.register(Earnings)
class EarningsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'partner_link',
        'amount',
        'source',
        'status',
        'date',
        'payout_link',
        'actions_column'
    )
    list_filter = ('status', 'source', 'date')
    search_fields = ('partner__name', 'payout__id')
    readonly_fields = ('created_at', 'updated_at', 'approval_date', 'rejection_date')
    fieldsets = (
        (None, {
            'fields': ('partner', 'created_by', 'amount', 'date', 'source', 'status')
        }),
        ('Payout Info', {
            'fields': ('payout', 'paid_date')
        }),
        ('Approval Info', {
            'fields': ('approval_date', 'rejection_date'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('System Info', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['approve_earnings', 'reject_earnings', 'mark_as_available']

    def partner_link(self, obj):
        url = reverse('admin:authentication_profile_change', args=[obj.partner.id])
        return format_html('<a href="{}">{}</a>', url, obj.partner.name)
    partner_link.short_description = "Partner"
    partner_link.admin_order_field = 'partner__name'

    def payout_link(self, obj):
        if obj.payout:
            url = reverse('admin:payouts_payout_change', args=[obj.payout.id])
            return format_html('<a href="{}">{}</a>', url, obj.payout.id)
        return "-"
    payout_link.short_description = "Payout"
    payout_link.admin_order_field = 'payout__id'

    def actions_column(self, obj):
        links = []
        if obj.status == Earnings.Status.PENDING_APPROVAL:
            url = reverse('admin:payouts_earnings_approve', args=[obj.id])
            links.append(f'<a href="{url}">Approve</a>')
            url = reverse('admin:payouts_earnings_reject', args=[obj.id])
            links.append(f'<a href="{url}">Reject</a>')
        if obj.status in [Earnings.Status.PENDING, Earnings.Status.PENDING_APPROVAL]:
            url = reverse('admin:payouts_earnings_mark_available', args=[obj.id])
            links.append(f'<a href="{url}">Mark Available</a>')
        return format_html(' | '.join(links)) if links else "-"
    actions_column.short_description = "Actions"
    actions_column.allow_tags = True

    def approve_earnings(self, request, queryset):
        count = 0
        for earning in queryset.filter(status=Earnings.Status.PENDING_APPROVAL):
            if earning.approve(request.user):
                count += 1
        self.message_user(request, f"Approved {count} earnings")
    approve_earnings.short_description = "Approve selected earnings"

    def reject_earnings(self, request, queryset):
        count = 0
        for earning in queryset.filter(status=Earnings.Status.PENDING_APPROVAL):
            if earning.reject(request.user):
                count += 1
        self.message_user(request, f"Rejected {count} earnings")
    reject_earnings.short_description = "Reject selected earnings"

    def mark_as_available(self, request, queryset):
        count = 0
        for earning in queryset.filter(status__in=[Earnings.Status.PENDING, Earnings.Status.PENDING_APPROVAL]):
            if earning.mark_as_available():
                count += 1
        self.message_user(request, f"Marked {count} earnings as available")
    mark_as_available.short_description = "Mark selected earnings as available"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/approve/',
                 self.admin_site.admin_view(self.approve_earning),
                 name='payouts_earnings_approve'),
            path('<path:object_id>/reject/',
                 self.admin_site.admin_view(self.reject_earning),
                 name='payouts_earnings_reject'),
            path('<path:object_id>/mark-available/',
                 self.admin_site.admin_view(self.mark_earning_available),
                 name='payouts_earnings_mark_available'),
        ]
        return custom_urls + urls

    def approve_earning(self, request, object_id, *args, **kwargs):
        from django.shortcuts import redirect
        earning = Earnings.objects.get(id=object_id)
        earning.approve(request.user)
        self.message_user(request, f"Earning {earning.id} approved")
        return redirect(reverse('admin:payouts_earnings_change', args=[object_id]))

    def reject_earning(self, request, object_id, *args, **kwargs):
        from django.shortcuts import redirect
        earning = Earnings.objects.get(id=object_id)
        earning.reject(request.user)
        self.message_user(request, f"Earning {earning.id} rejected")
        return redirect(reverse('admin:payouts_earnings_change', args=[object_id]))

    def mark_earning_available(self, request, object_id, *args, **kwargs):
        from django.shortcuts import redirect
        earning = Earnings.objects.get(id=object_id)
        earning.mark_as_available()
        self.message_user(request, f"Earning {earning.id} marked as available")
        return redirect(reverse('admin:payouts_earnings_change', args=[object_id]))