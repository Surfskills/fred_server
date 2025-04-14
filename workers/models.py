from django.conf import settings
from django.db import models
from django.utils import timezone
from custom.models import IDManager

class AcceptedOffer(models.Model):
    # Offer type choices
    OFFER_TYPE_CHOICES = (
        ('service', 'Service'),
        ('software', 'Software Request'),
        ('research', 'Research Request'),
    )
    
    # Payment status choices (consistent with other models)
    PENDING = 'pending'
    PAID = 'paid'
    FAILED = 'failed'
    
    PAYMENT_STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PAID, 'Paid'),
        (FAILED, 'Failed'),
    ]
    
    # Order status choices (consistent with other models)
    ORDER_STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('proceed_to_pay', 'Proceed to pay'),
        ('accepted', 'Accepted'),
        ('returned', 'Returned'),
    ]
    
    # Acceptance status choices (consistent with other models)
    ACCEPTANCE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('returned', 'Returned'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='accepted_offers'
    )
    
    # Foreign keys to different offer types
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
    
    shared_id = models.PositiveIntegerField(editable=False)
    title = models.CharField(max_length=255, blank=True)
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE_CHOICES)
    
    # Status fields consistent with other models
    acceptance_status = models.CharField(
        max_length=15,
        choices=ACCEPTANCE_STATUS_CHOICES,
        default='accepted'
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default=PENDING,
    )
    order_status = models.CharField(
        max_length=15,
        choices=ORDER_STATUS_CHOICES,
        default='processing',
    )
    
    original_data = models.JSONField(default=dict)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # DateTime fields
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Set shared_id if not provided
        if not self.shared_id:
            self.shared_id = IDManager.get_next_id()
            
        # Auto-populate fields based on offer type
        if self.offer_type == 'service' and self.service:
            self.title = self.service.title
            
            self.cost = self.service.cost
            # Copy statuses from service if not set
            if not self.acceptance_status:
                self.acceptance_status = self.service.acceptance_status
            if not self.payment_status:
                self.payment_status = self.service.payment_status
            if not self.order_status:
                self.order_status = self.service.order_status
                
        elif self.offer_type == 'software' and self.software_request:
            self.title = self.software_request.title
            self.cost = self.software_request.cost
            # Copy statuses from software request if not set
            if not self.acceptance_status:
                self.acceptance_status = self.software_request.acceptance_status
            if not self.payment_status:
                self.payment_status = self.software_request.payment_status
            if not self.order_status:
                self.order_status = self.software_request.order_status
                
        elif self.offer_type == 'research' and self.research_request:
            self.title = self.research_request.title
            self.cost = self.research_request.cost
            # Copy statuses from research request if not set
            if not self.acceptance_status:
                self.acceptance_status = self.research_request.acceptance_status
            if not self.payment_status:
                self.payment_status = self.research_request.payment_status
            if not self.order_status:
                self.order_status = self.research_request.order_status
        
        # If payment is pending, set order status to proceed_to_pay (consistent with other models)
        if self.payment_status == self.PENDING:
            self.order_status = 'proceed_to_pay'
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Accepted {self.get_offer_type_display()} - {self.title} (ID: {self.shared_id})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Accepted Offer'
        verbose_name_plural = 'Accepted Offers'