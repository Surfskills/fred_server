from django.contrib import admin
from .models import Service

class ServiceAdmin(admin.ModelAdmin):
    # Columns to display in the service list page
    list_display = (
        'title', 'user', 'cost', 'delivery_time', 
        'support_duration', 'service_id', 'phone_number'  # Added phone_number
    )
    
    # Fields to search by in the admin panel
    search_fields = (
        'title', 'service_id', 'user__email', 
        'phone_number'  # Added phone_number
    )
    
    # Fields to filter by in the sidebar of the admin list view
    list_filter = (
        'user', 'cost', 'delivery_time', 
        'support_duration', 'payment_status', 'order_status'
    )
    
    # Define the fields to show in the form when adding/editing a service
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'description', 'cost', 
                'phone_number', 'sizes'  # Added new fields
            )
        }),
        ('Service Details', {
            'fields': (
                'delivery_time', 'support_duration', 
                'features', 'process_link', 'service_id'
            )
        }),
        ('Status Information', {
            'fields': ('payment_status', 'order_status')
        }),
        ('User Information', {
            'fields': ('user',)
        }),
    )

    # Make the service ID editable on the form
    prepopulated_fields = {"service_id": ("title",)}

    # You can also define inline editing for related models, but it's not necessary here.
    # If there are any related models (e.g., ServiceCategory), you can add them as inline forms.

    model = Service

# Register the Service model with the custom admin interface
admin.site.register(Service, ServiceAdmin)