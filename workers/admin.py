from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import AcceptedOffer

from django.core.exceptions import ValidationError


class AcceptedOfferAdmin(admin.ModelAdmin):
    """
    Custom admin interface for the AcceptedOffer model.
    This provides enhanced functionality for managing accepted offers.
    """
    
    # List view configuration
    list_display = (
        'id', 
        'user', 
        'offer_type', 
        'status', 
        'accepted_at', 
        'completed_at', 
        'returned_at', 
        'get_offer_details', 
        'get_service_details', 
    )
    
    list_filter = (
        'status', 
        'accepted_at', 
        'completed_at', 
        'returned_at', 
        'user', 
    )
    
    search_fields = (
        'user__username', 
        'user__email', 
        'service__name', 
        'software_request__title', 
        'research_request__title',
    )
    
    # Prepopulate the fields based on model
    date_hierarchy = 'accepted_at'

    # Inline form for related models
    fieldsets = (
        (None, {
            'fields': (
                'user',
                'status',
                'accepted_at',
                'completed_at',
                'returned_at',
            ),
        }),
        (_('Offer Details'), {
            'fields': (
                'service',
                'software_request',
                'research_request',
            ),
        }),
    )

    # Define actions for changing multiple records at once
    actions = ['mark_as_in_progress', 'mark_as_completed', 'mark_as_returned']
    
    def mark_as_in_progress(self, request, queryset):
        """Action to mark selected offers as in-progress."""
        queryset.update(status='in_progress')
        self.message_user(request, _("Selected offers marked as 'In Progress'."))
        
    def mark_as_completed(self, request, queryset):
        """Action to mark selected offers as completed."""
        queryset.update(status='completed', completed_at=True)
        self.message_user(request, _("Selected offers marked as 'Completed'."))
        
    def mark_as_returned(self, request, queryset):
        """Action to mark selected offers as returned."""
        queryset.update(status='returned', returned_at=True)
        self.message_user(request, _("Selected offers marked as 'Returned'."))

    # Helper methods to display related information in list display
    def offer_type(self, obj):
        """Returns the offer type (Service, Software, Research)"""
        if obj.service:
            return "Service"
        elif obj.software_request:
            return "Software Request"
        elif obj.research_request:
            return "Research Request"
        return "Unknown"
    
    def get_offer_details(self, obj):
        """Returns a brief description of the offer"""
        if obj.service:
            return obj.service.name
        elif obj.software_request:
            return obj.software_request.title
        elif obj.research_request:
            return obj.research_request.title
        return "No Details"

    def get_service_details(self, obj):
        """Returns detailed info for the related service"""
        if obj.service:
            return f"{obj.service.name} ({obj.service.id})"
        return "-"

    get_offer_details.short_description = _('Offer Details')
    get_service_details.short_description = _('Service Details')

    # Customize form to allow only one related field to be populated at a time
    def clean(self, obj):
        """Ensure only one of service, software_request, or research_request is populated."""
        if sum([bool(obj.service), bool(obj.software_request), bool(obj.research_request)]) > 1:
            raise ValidationError(_('Only one of Service, SoftwareRequest, or ResearchRequest should be selected.'))
        return obj

    # Customize the ordering of entries
    ordering = ('-accepted_at',)

# Register the custom admin interface
admin.site.register(AcceptedOffer, AcceptedOfferAdmin)
