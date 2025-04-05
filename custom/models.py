from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

# Create a base model for ID sequence management
class IDManager(models.Model):
    """
    A model to manage the sequence of IDs across multiple models.
    This serves as a central point for ID generation.
    """
    # This model just needs to exist to create a sequence
    class Meta:
        managed = True

class BaseRequest(models.Model):
    REQUEST_TYPES = (
        ('software', 'Software'),
        ('research', 'Research'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

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
    
    # Acceptance status choices
    ACCEPTANCE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('returned', 'Returned'),
        ('completed', 'Completed'),
    ]
    
    # Keep the default id field but also add id_manager for shared sequence
    id_manager = models.OneToOneField(
        IDManager,
        on_delete=models.CASCADE,
        related_name='%(class)s_manager',
    )
    
    acceptance_status = models.CharField(
        max_length=15,
        choices=ACCEPTANCE_STATUS_CHOICES,
        default='pending',
        blank=True,
        null=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='%(class)s_requests'
    )
    title = models.CharField(max_length=255)
    project_description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', blank=True, null=True)
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default=PENDING,
        blank=True,
        null=True
    )
    order_status = models.CharField(
        max_length=15,
        choices=ORDER_STATUS_CHOICES,
        default='processing',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Create IDManager instance if this is a new object
        if not hasattr(self, 'id_manager') or self.id_manager is None:
            id_manager = IDManager.objects.create()
            self.id_manager = id_manager
            
        # If the payment status is pending, set order status to proceed_to_pay
        if self.payment_status == self.PENDING:
            self.order_status = 'proceed_to_pay'
            
        super().save(*args, **kwargs)
        
    # Add a property to get the shared ID
    @property
    def shared_id(self):
        return self.id_manager.id if self.id_manager else None

    class Meta:
        abstract = True

class SoftwareRequest(BaseRequest):
    BUDGET_RANGES = (
        ('1000-5000', '$1,000 - $5,000'),
        ('5000-10000', '$5,000 - $10,000'),
        ('10000+', '$10,000+'),
    )

    budget_range = models.CharField(max_length=20, choices=BUDGET_RANGES, blank=True, null=True)
    timeline = models.CharField(max_length=100, blank=True, null=True)
    frontend_languages = models.CharField(max_length=100, blank=True, null=True)
    frontend_frameworks = models.CharField(max_length=100, blank=True, null=True)
    backend_languages = models.CharField(max_length=100, blank=True, null=True)
    backend_frameworks = models.CharField(max_length=100, blank=True, null=True)
    ai_languages = models.CharField(max_length=100, blank=True, null=True)
    ai_frameworks = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.request_type = 'software'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Software Request: {self.title}"

class ResearchRequest(BaseRequest):
    STUDY_LEVEL_CHOICES = (
        ('HighSchool', 'High School'),
        ('Undergraduate', 'Undergraduate'),
        ('Masters', 'Masters'),
        ('PhD', 'PhD'),
        ('Doctoral', 'Doctoral'),
    )

    academic_writing_type = models.CharField(max_length=100, blank=True, null=True)
    writing_technique = models.CharField(max_length=100, blank=True, null=True)
    academic_writing_style = models.CharField(max_length=100, blank=True, null=True)
    critical_writing_type = models.CharField(max_length=100, blank=True, null=True)
    critical_thinking_skill = models.CharField(max_length=100, blank=True, null=True)
    critical_writing_structure = models.CharField(max_length=100, blank=True, null=True)
    discussion_type = models.CharField(max_length=100, blank=True, null=True)
    discussion_component = models.CharField(max_length=100, blank=True, null=True)
    citation_style = models.CharField(max_length=100, blank=True, null=True)
    number_of_pages = models.IntegerField(default=1, blank=True, null=True)
    number_of_references = models.IntegerField(default=0, blank=True, null=True)
    study_level = models.CharField(max_length=20, choices=STUDY_LEVEL_CHOICES, default='Undergraduate', blank=True, null=True)

    def save(self, *args, **kwargs):
        self.request_type = 'research'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Research Request: {self.title}"


class SoftwareRequestFile(models.Model):
    software_request = models.ForeignKey(SoftwareRequest, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="software_request_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

class ResearchRequestFile(models.Model):
    research_request = models.ForeignKey(ResearchRequest, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="research_request_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)