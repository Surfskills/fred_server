from django.db import models
from custom.models import BaseRequest, SoftwareRequest, ResearchRequest
from service.models import Service

class AcceptedOffer(BaseRequest):
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
    offer_type = models.CharField(max_length=255, null=True, blank=True)

    
    # Foreign key relationships to Service and Custom requests (SoftwareRequest/ResearchRequest)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    software_request = models.ForeignKey(SoftwareRequest, on_delete=models.CASCADE, null=True, blank=True)
    research_request = models.ForeignKey(ResearchRequest, on_delete=models.CASCADE, null=True, blank=True)
    
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
