from django.conf import settings
from django.db import models
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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='accepted_offers'
    )
    
    # Updated foreign keys with proper string references to avoid circular imports
    service = models.ForeignKey(
        'service.Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_offers'
    )
    software_request = models.ForeignKey(
        'custom.SoftwareRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_offers'
    )
    research_request = models.ForeignKey(
        'custom.ResearchRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_offers'
    )
    
    # Changed to PositiveIntegerField to match our shared_id implementation
    shared_id = models.PositiveIntegerField(editable=False)
    title = models.CharField(max_length=255, blank=True)
    request_type = models.CharField(max_length=20, blank=True, null=True)
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='accepted'
    )
    
    original_data = models.JSONField(default=dict)
    
    # DateTime fields with proper defaults
    accepted_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-populate fields based on offer type
        if not self.shared_id:
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
        return f"Accepted {self.get_offer_type_display()} - {self.title} (ID: {self.shared_id})"

    class Meta:
        ordering = ['-accepted_at']
        verbose_name = 'Accepted Offer'
        verbose_name_plural = 'Accepted Offers'