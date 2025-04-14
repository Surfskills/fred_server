
# from django.contrib import admin
# from django.utils.html import format_html
# from .models import AcceptedOffer


# class AcceptedOfferAdmin(admin.ModelAdmin):
#     list_display = ('id', 'offer_type', 'status', 'accepted_at', 'related_object_link')
#     list_filter = ('status', 'offer_type', 'accepted_at')
#     search_fields = ('original_data',)  # Change to a tuple (or list)
#     readonly_fields = ('accepted_at', 'started_at', 'completed_at', 'returned_at')
#     date_hierarchy = 'accepted_at'
    
#     fieldsets = (
#         ('Offer Information', {
#             'fields': ('offer_type', 'status')
#         }),
#         ('Related Objects', {
#             'fields': ('service', 'software_request', 'research_request')
#         }),
#         ('Original Data', {
#             'fields': ('original_data',),
#             'classes': ('collapse',),
#         }),
#         ('Timestamps', {
#             'fields': ('accepted_at', 'started_at', 'completed_at', 'returned_at'),
#         }),
#     )

#     def related_object_link(self, obj):
#         """Generate a link to the related object admin page based on offer_type"""
#         if obj.offer_type == 'service' and obj.service:
#             url = f"/admin/service/service/{obj.service.id}/change/"
#             return format_html('<a href="{}">{}</a>', url, str(obj.service))
#         elif obj.offer_type == 'software' and obj.software_request:
#             url = f"/admin/custom/softwarerequest/{obj.software_request.id}/change/"
#             return format_html('<a href="{}">{}</a>', url, str(obj.software_request))
#         elif obj.offer_type == 'research' and obj.research_request:
#             url = f"/admin/custom/researchrequest/{obj.research_request.id}/change/"
#             return format_html('<a href="{}">{}</a>', url, str(obj.research_request))
#         return "—"
#     related_object_link.short_description = 'Related Object'

#     def save_model(self, request, obj, form, change):
#         """Auto-update timestamps when status changes in admin"""
#         from django.utils import timezone
        
#         if change:  # Only for existing objects
#             original_obj = self.model.objects.get(pk=obj.pk)
#             if original_obj.status != obj.status:
#                 if obj.status == 'in_progress' and not obj.started_at:
#                     obj.started_at = timezone.now()
#                 elif obj.status == 'completed' and not obj.completed_at:
#                     obj.completed_at = timezone.now()
#                 elif obj.status == 'returned' and not obj.returned_at:
#                     obj.returned_at = timezone.now()
        
#         super().save_model(request, obj, form, change)

# admin.site.register(AcceptedOffer, AcceptedOfferAdmin)
