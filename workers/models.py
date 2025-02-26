from django.db import models
from django.conf import settings
from django.forms import ValidationError
from service.models import Service
from custom.models import SoftwareRequest, ResearchRequest
from django.utils import timezone

class AcceptedOffer(models.Model):
    ACCEPTED_STATUS_CHOICES = (
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('returned', 'Returned'),
    )
    
    OFFER_TYPE_CHOICES = (
        ('service', 'Service'),
        ('software', 'Software Request'),
        ('research', 'Research Request'),
    )
    
    # User who accepted the offer
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='accepted_offers'
    )
    
    # Foreign key relationships to Service, SoftwareRequest, and ResearchRequest
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    software_request = models.ForeignKey(SoftwareRequest, on_delete=models.CASCADE, null=True, blank=True)
    research_request = models.ForeignKey(ResearchRequest, on_delete=models.CASCADE, null=True, blank=True)
    
    # Offer type (service, software, or research)
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE_CHOICES)
    
    # Status and timing fields
    status = models.CharField(max_length=20, choices=ACCEPTED_STATUS_CHOICES, default='accepted')
    accepted_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    returned_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"Offer {self.id} - {self.status}"

    class Meta:
        db_table = 'accepted_offers'
        unique_together = ('user', 'service', 'software_request', 'research_request')
        
    def clean(self):
        """Ensure only one of the offer fields is set."""
        offer_fields = [self.service, self.software_request, self.research_request]
        # Count how many of the fields are filled
        if sum([1 for field in offer_fields if field is not None]) > 1:
            raise ValidationError('Only one of service, software_request, or research_request can be set.')
