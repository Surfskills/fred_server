from django.conf import settings
from django.db import models

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
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='%(class)s_requests'
    )
    title = models.CharField(max_length=255)
    project_description = models.TextField()
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
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
        # If the payment status is pending, set order status to proceed_to_pay
        if self.payment_status == self.PENDING:
            self.order_status = 'proceed_to_pay'
        super().save(*args, **kwargs)

    class Meta:
        abstract = True

class SoftwareRequest(BaseRequest):
    BUDGET_RANGES = (
        ('1000-5000', '$1,000 - $5,000'),
        ('5000-10000', '$5,000 - $10,000'),
        ('10000+', '$10,000+'),
    )

    budget_range = models.CharField(max_length=20, choices=BUDGET_RANGES)
    timeline = models.CharField(max_length=100)
    frontend_languages = models.CharField(max_length=100)
    frontend_frameworks = models.CharField(max_length=100)
    backend_languages = models.CharField(max_length=100)
    backend_frameworks = models.CharField(max_length=100)
    ai_languages = models.CharField(max_length=100)
    ai_frameworks = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        self.request_type = 'software'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Software Request: {self.title}"

class ResearchRequest(BaseRequest):
    academic_writing_type = models.CharField(max_length=100)
    writing_technique = models.CharField(max_length=100)
    research_paper_structure = models.CharField(max_length=100)
    academic_writing_style = models.CharField(max_length=100)
    research_paper_writing_process = models.CharField(max_length=100)
    critical_writing_type = models.CharField(max_length=100)
    critical_thinking_skill = models.CharField(max_length=100)
    critical_writing_structure = models.CharField(max_length=100)
    discussion_type = models.CharField(max_length=100)
    discussion_component = models.CharField(max_length=100)
    academic_writing_tool = models.CharField(max_length=100)
    research_paper_database = models.CharField(max_length=100)
    plagiarism_checker = models.CharField(max_length=100)
    reference_management_tool = models.CharField(max_length=100)
    academic_discussion_type = models.CharField(max_length=100)
    citation_style = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        self.request_type = 'research'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Research Request: {self.title}"