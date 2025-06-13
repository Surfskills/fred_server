# admin.py - Comprehensive admin interface
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum, Q
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import render, get_object_or_404
from django.urls import path
from django.template.response import TemplateResponse
import csv
from datetime import datetime, timedelta

from .models import (
    BaseService, SoftwareService, ResearchService, CustomService,
    ServiceFile, Freelancer, OrderStatusHistory, OrderComment, Bid
)


# Custom Filters
class StatusFilter(SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return BaseService.STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class PaymentStatusFilter(SimpleListFilter):
    title = 'Payment Status'
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        return BaseService.PAYMENT_STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment_status=self.value())
        return queryset


class AssignmentFilter(SimpleListFilter):
    title = 'Assignment Status'
    parameter_name = 'assignment'

    def lookups(self, request, model_admin):
        return (
            ('assigned', 'Assigned'),
            ('unassigned', 'Unassigned'),
            ('overdue', 'Overdue'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'assigned':
            return queryset.filter(assigned_to__isnull=False)
        elif self.value() == 'unassigned':
            return queryset.filter(assigned_to__isnull=True)
        elif self.value() == 'overdue':
            return queryset.filter(
                deadline__lt=timezone.now(),
                status__in=['available', 'assigned', 'in_progress']
            )
        return queryset


class ServiceTypeFilter(SimpleListFilter):
    title = 'Service Type'
    parameter_name = 'service_type'

    def lookups(self, request, model_admin):
        return BaseService.SERVICE_TYPES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(service_type=self.value())
        return queryset


# class FreelancerAvailabilityFilter(SimpleListFilter):
#     title = 'Availability'
#     parameter_name = 'availability'

#     def lookups(self, request, model_admin):
#         return (
#             ('available', 'Available'),
#             ('busy', 'Busy'),
#         )

#     def queryset(self, request, queryset):
#         if self.value() == 'available':
#             return queryset.filter(is_available=True)
#         elif self.value() == 'busy':
#             return queryset.filter(is_available=False)
#         return queryset


# Inline Classes
class ServiceFileInline(admin.TabularInline):
    model = ServiceFile
    extra = 1
    fields = ('file', 'file_type', 'description', 'uploaded_by', 'file_size_display')
    readonly_fields = ('uploaded_by', 'file_size_display')

    def file_size_display(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return "N/A"
    file_size_display.short_description = "File Size"


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    fields = ('previous_status', 'new_status', 'changed_by', 'changed_at', 'notes')
    readonly_fields = ('changed_by', 'changed_at')


class OrderCommentInline(admin.TabularInline):
    model = OrderComment
    extra = 1
    fields = ('author', 'message', 'is_internal', 'created_at')
    readonly_fields = ('author', 'created_at')


class BidInline(admin.TabularInline):
    model = Bid
    extra = 0
    fields = ('freelancer', 'bid_amount', 'estimated_hours', 'status', 'created_at')
    readonly_fields = ('created_at',)


# Custom Admin Actions
def export_orders_to_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Order ID', 'Title', 'Client', 'Service Type', 'Status', 'Payment Status',
        'Assigned To', 'Cost', 'Deadline', 'Created', 'Priority'
    ])
    
    for order in queryset:
        writer.writerow([
            order.id,
            order.title,
            order.user.email,
            order.get_service_type_display(),
            order.get_status_display(),
            order.get_payment_status_display(),
            order.assigned_to_name or 'Unassigned',
            order.cost or 0,
            order.deadline.strftime('%Y-%m-%d %H:%M') if order.deadline else 'No deadline',
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.get_priority_display()
        ])
    
    return response
export_orders_to_csv.short_description = "Export selected orders to CSV"


def assign_to_freelancer(modeladmin, request, queryset):
    if 'apply' in request.POST:
        freelancer_id = request.POST.get('freelancer')
        try:
            freelancer = Freelancer.objects.get(id=freelancer_id)
            updated_count = 0
            for order in queryset:
                if not order.assigned_to:
                    order.assign_to_freelancer(freelancer)
                    updated_count += 1
            messages.success(request, f'{updated_count} orders assigned to {freelancer.name}')
            return HttpResponseRedirect(request.get_full_path())
        except Freelancer.DoesNotExist:
            messages.error(request, 'Selected freelancer not found')
    
    freelancers = Freelancer.objects.filter(is_available=True)
    return render(request, 'admin/assign_freelancer.html', {
        'orders': queryset,
        'freelancers': freelancers,
        'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
    })
assign_to_freelancer.short_description = "Assign to freelancer"


def mark_as_completed(modeladmin, request, queryset):
    updated = queryset.filter(status__in=['in_progress', 'assigned']).update(
        status='completed',
        completed_at=timezone.now()
    )
    messages.success(request, f'{updated} orders marked as completed')
mark_as_completed.short_description = "Mark as completed"


def mark_as_cancelled(modeladmin, request, queryset):
    updated = queryset.exclude(status='completed').update(status='cancelled')
    messages.success(request, f'{updated} orders cancelled')
mark_as_cancelled.short_description = "Cancel orders"


# # Main Admin Classes
# @admin.register(Freelancer)
# class FreelancerAdmin(admin.ModelAdmin):
#     list_display = (
#         'id', 'name', 'freelancer_type', 'email', 'is_available', 
#         'hourly_rate', 'active_orders_count', 'total_orders_count',
#         'skills_display', 'created_at'
#     )
#     list_filter = (
#         'freelancer_type', FreelancerAvailabilityFilter, 'created_at'
#     )
#     search_fields = ('id', 'name', 'email', 'phone')
#     list_editable = ('is_available', 'hourly_rate')
#     readonly_fields = ('created_at', 'updated_at', 'active_orders_count', 'total_orders_count')
    
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('id', 'user', 'name', 'email', 'phone')
#         }),
#         ('Professional Details', {
#             'fields': ('freelancer_type', 'skills', 'hourly_rate', 'is_available')
#         }),
#         ('Statistics', {
#             'fields': ('active_orders_count', 'total_orders_count'),
#             'classes': ('collapse',)
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )

#     def skills_display(self, obj):
#         return ", ".join(
#             skill.get("name", "") for skill in obj.skills if isinstance(skill, dict)
#         )

#     def active_orders_count(self, obj):
#         return obj.assigned_orders.filter(status__in=['assigned', 'in_progress']).count()
#     active_orders_count.short_description = 'Active Orders'

#     def total_orders_count(self, obj):
#         return obj.assigned_orders.count()
#     total_orders_count.short_description = 'Total Orders'

#     def get_queryset(self, request):
#         queryset = super().get_queryset(request)
#         return queryset.annotate(
#             active_orders=Count('assigned_orders', filter=Q(assigned_orders__status__in=['assigned', 'in_progress'])),
#             total_orders=Count('assigned_orders')
#         )


@admin.register(BaseService)
class BaseServiceAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title_short', 'client_info', 'service_type', 'status_badge', 
        'payment_status_badge', 'assigned_to_info', 'cost_display', 
        'deadline_info', 'priority_badge', 'priority', 'created_at'  # Added 'priority' here
    )
    list_filter = (
        StatusFilter, PaymentStatusFilter, ServiceTypeFilter, 
        AssignmentFilter, 'priority', 'created_at', 'deadline'
    )
    search_fields = ('id', 'title', 'description', 'user__email', 'assigned_to__name')
    list_editable = ('priority',) 
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'assigned_at', 'started_at', 
        'completed_at', 'client_id', 'is_overdue', 'time_remaining_display'
    )
    
    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'title', 'description', 'service_type', 'user', 'client_id')
        }),
        ('Status & Assignment', {
            'fields': (
                'status', 'payment_status', 'acceptance_status', 
                'priority', 'assigned_to', 'assigned_at'
            )
        }),
        ('Financial & Timeline', {
            'fields': ('cost', 'bid_amount', 'deadline', 'estimated_hours', 'actual_hours', 'time_remaining_display', 'is_overdue')
        }),
        ('Additional Information', {
            'fields': ('requirements', 'tags', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ServiceFileInline, OrderStatusHistoryInline, OrderCommentInline, BidInline]
    actions = [export_orders_to_csv, assign_to_freelancer, mark_as_completed, mark_as_cancelled]
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view), name='services_dashboard'),
            path('<str:order_id>/assign/', self.admin_site.admin_view(self.assign_view), name='assign_order'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        # Statistics for dashboard
        total_orders = BaseService.objects.count()
        status_counts = BaseService.objects.values('status').annotate(count=Count('id'))
        payment_status_counts = BaseService.objects.values('payment_status').annotate(count=Count('id'))
        
        overdue_orders = BaseService.objects.filter(
            deadline__lt=timezone.now(),
            status__in=['available', 'assigned', 'in_progress']
        ).count()
        
        total_revenue = BaseService.objects.filter(
            payment_status='paid'
        ).aggregate(total=Sum('cost'))['total'] or 0
        
        pending_revenue = BaseService.objects.filter(
            payment_status='pending'
        ).aggregate(total=Sum('cost'))['total'] or 0
        
        recent_orders = BaseService.objects.order_by('-created_at')[:10]
        
        context = {
            'title': 'Services Dashboard',
            'total_orders': total_orders,
            'status_counts': {item['status']: item['count'] for item in status_counts},
            'payment_status_counts': {item['payment_status']: item['count'] for item in payment_status_counts},
            'overdue_orders': overdue_orders,
            'total_revenue': total_revenue,
            'pending_revenue': pending_revenue,
            'recent_orders': recent_orders,
        }
        
        return TemplateResponse(request, 'admin/services_dashboard.html', context)

    def assign_view(self, request, order_id):
        order = get_object_or_404(BaseService, id=order_id)
        freelancers = Freelancer.objects.filter(is_available=True)
        
        if request.method == 'POST':
            freelancer_id = request.POST.get('freelancer')
            notes = request.POST.get('notes', '')
            
            try:
                freelancer = Freelancer.objects.get(id=freelancer_id)
                order.assign_to_freelancer(freelancer)
                
                # Create status history
                OrderStatusHistory.objects.create(
                    order=order,
                    previous_status=order.status,
                    new_status='assigned',
                    changed_by=request.user,
                    notes=notes
                )
                
                messages.success(request, f'Order {order.id} assigned to {freelancer.name}')
                return HttpResponseRedirect(reverse('admin:services_baseservice_change', args=[order.id]))
            except Freelancer.DoesNotExist:
                messages.error(request, 'Selected freelancer not found')
        
        context = {
            'title': f'Assign Order {order.id}',
            'order': order,
            'freelancers': freelancers,
        }
        
        return TemplateResponse(request, 'admin/assign_order.html', context)

    def title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_short.short_description = 'Title'

    def client_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.user.email,
            obj.client_id
        )
    client_info.short_description = 'Client'

    def status_badge(self, obj):
        colors = {
            'available': 'green',
            'assigned': 'blue',
            'in_progress': 'orange',
            'completed': 'purple',
            'cancelled': 'red',
            'on_hold': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def payment_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'failed': 'red',
            'refunded': 'purple'
        }
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment'

    def assigned_to_info(self, obj):
        if obj.assigned_to:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.assigned_to.name,
                obj.assigned_to.freelancer_type
            )
        return format_html('<span style="color: red;">Unassigned</span>')
    assigned_to_info.short_description = 'Assigned To'

    def cost_display(self, obj):
        if obj.cost:
            return f'${obj.cost:,.2f}'
        return 'N/A'
    cost_display.short_description = 'Cost'

    def deadline_info(self, obj):
        if not obj.deadline:
            return 'No deadline'
        
        now = timezone.now()
        if obj.deadline < now and obj.status not in ['completed', 'cancelled']:
            return format_html(
                '<span style="color: red; font-weight: bold;">OVERDUE<br>{}</span>',
                obj.deadline.strftime('%m/%d/%Y %H:%M')
            )
        elif obj.deadline < now + timedelta(days=1):
            return format_html(
                '<span style="color: orange; font-weight: bold;">DUE SOON<br>{}</span>',
                obj.deadline.strftime('%m/%d/%Y %H:%M')
            )
        else:
            return obj.deadline.strftime('%m/%d/%Y %H:%M')
    deadline_info.short_description = 'Deadline'

    def priority_badge(self, obj):
        colors = {
            'low': '#28a745',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'urgent': '#dc3545'
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; text-transform: uppercase;">{}</span>',
            color,
            obj.priority
        )
    priority_badge.short_description = 'Priority'

    def time_remaining_display(self, obj):
        time_remaining = obj.time_remaining
        if time_remaining:
            days = time_remaining.days
            hours, remainder = divmod(time_remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return "Expired" if obj.is_overdue else "No deadline"
    time_remaining_display.short_description = 'Time Remaining'


@admin.register(SoftwareService)
class SoftwareServiceAdmin(BaseServiceAdmin):
    fieldsets = BaseServiceAdmin.fieldsets + (
        ('Software Development Details', {
            'fields': (
                'budget_range', 'timeline', 'frontend_languages', 'frontend_frameworks',
                'backend_languages', 'backend_frameworks', 'ai_languages', 'ai_frameworks'
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(ResearchService)
class ResearchServiceAdmin(BaseServiceAdmin):
    fieldsets = BaseServiceAdmin.fieldsets + (
        ('Research Details', {
            'fields': (
                'academic_writing_type', 'writing_technique', 'academic_writing_style',
                'critical_writing_type', 'critical_thinking_skill', 'critical_writing_structure',
                'discussion_type', 'discussion_component', 'citation_style',
                'number_of_pages', 'number_of_references', 'study_level'
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(CustomService)
class CustomServiceAdmin(BaseServiceAdmin):
    fieldsets = BaseServiceAdmin.fieldsets + (
        ('Custom Service Details', {
            'fields': (
                'sizes', 'phone_number', 'delivery_time', 'support_duration',
                'features', 'process_link', 'service_id'
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(ServiceFile)
class ServiceFileAdmin(admin.ModelAdmin):
    list_display = ('service', 'file_name', 'file_type', 'file_size_display', 'uploaded_by', 'uploaded_at')
    list_filter = ('file_type', 'uploaded_at')
    search_fields = ('service__id', 'service__title', 'description')
    readonly_fields = ('uploaded_at', 'file_size', 'file_size_display')

    def file_name(self, obj):
        return obj.file.name.split('/')[-1] if obj.file else 'N/A'
    file_name.short_description = 'File Name'

    def file_size_display(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return "N/A"
    file_size_display.short_description = "File Size"


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'previous_status', 'new_status', 'changed_by', 'changed_at')
    list_filter = ('new_status', 'previous_status', 'changed_at')
    search_fields = ('order__id', 'order__title', 'notes')
    readonly_fields = ('changed_at',)


@admin.register(OrderComment)
class OrderCommentAdmin(admin.ModelAdmin):
    list_display = ('order', 'author', 'message_short', 'is_internal', 'created_at')
    list_filter = ('is_internal', 'created_at')
    search_fields = ('order__id', 'order__title', 'message', 'author__email')
    readonly_fields = ('created_at', 'updated_at')

    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Message'


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = (
        'order', 'freelancer', 'bid_amount', 'estimated_hours', 
        'status_badge', 'created_at', 'approved_by'
    )
    list_filter = ('status', 'created_at', 'approved_at')
    search_fields = ('order__id', 'order__title', 'freelancer__name', 'proposal')
    readonly_fields = ('created_at', 'updated_at', 'approved_at')
    
    fieldsets = (
        ('Bid Information', {
            'fields': ('order', 'freelancer', 'bid_amount', 'estimated_hours', 'proposal')
        }),
        ('Status', {
            'fields': ('status', 'approved_by', 'approved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'withdrawn': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    actions = ['approve_bids', 'reject_bids']

    def approve_bids(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        messages.success(request, f'{updated} bids approved')
    approve_bids.short_description = "Approve selected bids"

    def reject_bids(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='rejected')
        messages.success(request, f'{updated} bids rejected')
    reject_bids.short_description = "Reject selected bids"


# Custom admin site configuration
admin.site.site_header = "Service Management Admin"
admin.site.site_title = "Service Admin"
admin.site.index_title = "Welcome to Service Management Administration"