import uuid
from django.conf import settings
from django.db import models
from django.db import transaction
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

from custom.models import IDManager



class Service(models.Model):
    # User associated with the service
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='user_services'
    )
    
    # Other fields for service details
    title = models.CharField(max_length=255)
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    # New fields for sizes and phone number
    sizes = models.JSONField(default=dict)  
    phone_number = models.CharField(max_length=20, blank=True, null=True) 
    
    delivery_time = models.CharField(max_length=100)  # e.g., "2-3 weeks"
    support_duration = models.CharField(max_length=100)  # e.g., "1 month"
    features = models.JSONField()  # Stores an array of features
    process_link = models.URLField()
    service_id = models.CharField(max_length=100)
    shared_id = models.PositiveIntegerField(unique=True, editable=False)
    
    # Payment status choices
    PENDING = 'pending'
    PAID = 'paid'
    FAILED = 'failed'
    
    PAYMENT_STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PAID, 'Paid'),
        (FAILED, 'Failed'),
    ]
    
    # Order status choices
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
    
    # Add new acceptance status choices
    ACCEPTANCE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('returned', 'Returned'),
        ('completed', 'Completed'),
    ]
    
    acceptance_status = models.CharField(
        max_length=15,
        choices=ACCEPTANCE_STATUS_CHOICES,
        default='pending',
        blank=True,
        null=True
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
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.shared_id:
            self.shared_id = IDManager.get_next_id()
            
        # Generate service_id if not provided
        if not self.service_id:
            self.service_id = f"svc-{str(uuid.uuid4())[:8]}"
            
        # If the payment status is pending, set order status to "waiting_payment"
        if self.payment_status == self.PENDING:
            self.order_status = 'proceed_to_pay'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title

    class Meta:
        unique_together = ('user', 'title')  # Ensures a user can't have duplicate service titles
    
class ServiceFile(models.Model):
    # Files linked to the Service (order)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="service_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.service.title} - {self.file.name}"