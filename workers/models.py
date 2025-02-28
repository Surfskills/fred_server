from django.conf import settings
from django.db import models
from service.models import Service
from custom.models import SoftwareRequest, ResearchRequest
from django.utils import timezone



class AcceptedOffer(models.Model):
    STATUS_CHOICES = (
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
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='accepted_offers')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_offers')
    software_request = models.ForeignKey(SoftwareRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_offers')
    research_request = models.ForeignKey(ResearchRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_offers')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='accepted')
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE_CHOICES)
    
    # Store original offer data
    original_data = models.JSONField(default=dict)
    
    # Timestamps
    accepted_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Accepted {self.offer_type}"