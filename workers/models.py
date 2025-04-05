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
    
    shared_id = models.CharField(max_length=255, editable=False)
    title = models.CharField(max_length=255, blank=True)
    request_type = models.CharField(max_length=20, blank=True, null=True)
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='accepted')
    
    original_data = models.JSONField(default=dict)
    
    accepted_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.offer_type == 'service' and self.service:
            self.shared_id = self.service.shared_id
            self.title = self.service.title
            self.request_type = 'service'
        elif self.offer_type == 'software' and self.software_request:
            self.shared_id = self.software_request.shared_id
            self.title = self.software_request.title
            self.request_type = 'software'
        elif self.offer_type == 'research' and self.research_request:
            self.shared_id = self.research_request.shared_id
            self.title = self.research_request.title
            self.request_type = 'research'
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Accepted {self.offer_type} - {self.title} ({self.shared_id})"
