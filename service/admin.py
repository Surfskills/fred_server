from django.contrib import admin
from django.utils.html import format_html
from .models import Service

# Service admin remains unchanged
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'user', 'cost', 'delivery_time', 
        'support_duration', 'service_id', 'phone_number', 'acceptance_status',
    )
    search_fields = (
        'title', 'service_id', 'user__email', 
        'phone_number'
    )
    list_filter = (
        'user', 'cost', 'delivery_time', 
        'support_duration', 'payment_status', 'order_status', 'acceptance_status'
    )
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'description', 'cost', 
                'phone_number', 'sizes'
            )
        }),
        ('Service Details', {
            'fields': (
                'delivery_time', 'support_duration', 
                'features', 'process_link', 'service_id'
            )
        }),
        ('Status Information', {
            'fields': ('payment_status', 'order_status', 'acceptance_status')
        }),
        ('User Information', {
            'fields': ('user',)
        }),
    )
    prepopulated_fields = {"service_id": ("title",)}
    model = Service

admin.site.register(Service, ServiceAdmin)