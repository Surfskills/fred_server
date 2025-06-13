# Enhanced models.py with improved start_working workflow

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
import django_filters
from polymorphic.models import PolymorphicModel

from django.db import models

from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Freelancer(models.Model):
    """Enhanced Freelancer model for profile management"""
    
    FREELANCER_TYPES = (
        ('development', 'Software Development'),
        ('web_development', 'Web Development'),
        ('mobile_development', 'Mobile Development'),
        ('design', 'Design & Creative'),
        ('ui_ux', 'UI/UX Design'),
        ('marketing', 'Digital Marketing'),
        ('content_writing', 'Content Writing'),
        ('copywriting', 'Copywriting'),
        ('data_science', 'Data Science'),
        ('consulting', 'Business Consulting'),
        ('translation', 'Translation'),
        ('virtual_assistant', 'Virtual Assistant'),
        ('other', 'Other'),
    )
    
    EXPERIENCE_LEVELS = (
        ('beginner', 'Beginner (0-1 years)'),
        ('intermediate', 'Intermediate (1-3 years)'),
        ('advanced', 'Advanced (3-5 years)'),
        ('expert', 'Expert (5+ years)'),
    )
    
    AVAILABILITY_STATUS = (
        ('available', 'Available Now'),
        ('busy', 'Busy'),
        ('partially_available', 'Partially Available'),
        ('unavailable', 'Unavailable'),
    )

    # Primary fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='freelancer_profile'
    )
    
    # Profile information
    display_name = models.CharField(max_length=100, blank=True, null=True, help_text="Professional display name")
    bio = models.TextField(max_length=1000, blank=True, help_text="Professional bio/summary")
    title = models.CharField(max_length=200, blank=True, help_text="Professional title")
    
    # Categorization
    freelancer_type = models.CharField(max_length=30, choices=FREELANCER_TYPES, default='other')
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVELS, default='beginner')
    
    # Skills and expertise
    skills = models.JSONField(default=list, help_text="List of skills")
    specializations = models.JSONField(default=list, help_text="List of specializations")
    
    # Availability and rates
    is_available = models.BooleanField(default=True)
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_STATUS, default='available')
    hourly_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(5.00)]
    )
    minimum_project_budget = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(50.00)]
    )
    
    # Work preferences
    preferred_project_duration = models.CharField(
        max_length=20,
        choices=[
            ('short', 'Short-term (< 1 month)'),
            ('medium', 'Medium-term (1-3 months)'),
            ('long', 'Long-term (3+ months)'),
            ('any', 'Any duration'),
        ],
        default='any'
    )
    
    max_concurrent_projects = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    
    # Location and timezone
    location = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=50, blank=True)
    willing_to_travel = models.BooleanField(default=False)
    
    # Portfolio and credentials
    portfolio_url = models.URLField(blank=True)
    resume = models.FileField(upload_to='freelancer_resumes/', blank=True, null=True)
    
    # Languages
    languages = models.JSONField(
        default=list, 
        help_text="List of languages with proficiency levels"
    )
    
    # Rating and statistics
    total_projects_completed = models.IntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0.00), MaxValueValidator(5.00)]
    )
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Profile completion
    profile_completion_score = models.IntegerField(default=0)
    is_profile_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.display_name} ({self.get_freelancer_type_display()})"

    @property
    def name(self):
        return self.display_name or self.user.username 

    @property
    def email(self):
        """Convenient access to user email"""
        return self.user.email

    @property
    def phone(self):
        """Convenient access to user phone"""
        return self.user.phone_number

    def calculate_profile_completion(self):
        """Calculate profile completion percentage"""
        completion_factors = [
            bool(self.display_name),
            bool(self.bio),
            bool(self.title),
            len(self.skills) >= 3,
            bool(self.hourly_rate),
            bool(self.location),
            bool(self.user.profile_picture),
            len(self.portfolio_items.all()) >= 1,
            len(self.languages) >= 1,
            bool(self.experience_level),
        ]
        
        completion_score = int((sum(completion_factors) / len(completion_factors)) * 100)
        self.profile_completion_score = completion_score
        self.save(update_fields=['profile_completion_score'])
        
        # Also update user profile completion
        self.user.calculate_profile_completion()
        
        return completion_score

    def update_statistics(self):
        """Update freelancer statistics"""
        completed_orders = self.assigned_orders.filter(status='completed')
        self.total_projects_completed = completed_orders.count()
        
        # Calculate average rating from reviews
        reviews = FreelancerReview.objects.filter(freelancer=self)
        if reviews.exists():
            self.average_rating = reviews.aggregate(
                avg_rating=models.Avg('rating')
            )['avg_rating'] or 0.00
        
        # Calculate total earnings (you might want to add a Payment model)
        # self.total_earnings = completed_orders.aggregate(
        #     total=models.Sum('cost')
        # )['total'] or 0.00
        
        self.save(update_fields=['total_projects_completed', 'average_rating'])

    def can_take_new_projects(self):
        """Check if freelancer can take new projects"""
        if not self.is_available:
            return False
        
        active_projects = self.assigned_orders.filter(
            status__in=['assigned', 'start_working', 'in_progress']
        ).count()
        
        return active_projects < self.max_concurrent_projects

    class Meta:
        indexes = [
            models.Index(fields=['freelancer_type']),
            models.Index(fields=['is_available']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['created_at']),
            models.Index(fields=['hourly_rate']),
        ]
        ordering = ['-average_rating', '-total_projects_completed']


class FreelancerPortfolio(models.Model):
    """Portfolio items for freelancers"""
    freelancer = models.ForeignKey(
        Freelancer, 
        on_delete=models.CASCADE, 
        related_name='portfolio_items'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=1000)
    project_url = models.URLField(blank=True)
    image = models.ImageField(upload_to='portfolio_images/', blank=True, null=True)
    technologies_used = models.JSONField(default=list)
    project_type = models.CharField(max_length=50, blank=True)
    completion_date = models.DateField(blank=True, null=True)
    client_name = models.CharField(max_length=100, blank=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.freelancer.display_name} - {self.title}"

    class Meta:
        ordering = ['-is_featured', '-created_at']


class FreelancerReview(models.Model):
    """Reviews for freelancers"""
    freelancer = models.ForeignKey(
        Freelancer, 
        on_delete=models.CASCADE, 
        related_name='reviews'
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='given_reviews'
    )
    order = models.OneToOneField(
        'BaseService', 
        on_delete=models.CASCADE,
        related_name='review',
        blank=True,
        null=True
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review_text = models.TextField(max_length=1000, blank=True)
    communication_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    quality_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    timeliness_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    would_recommend = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.freelancer.display_name} by {self.client.email}"

    class Meta:
        unique_together = ('freelancer', 'client', 'order')
        ordering = ['-created_at']


class FreelancerCertification(models.Model):
    """Certifications and credentials for freelancers"""
    freelancer = models.ForeignKey(
        Freelancer, 
        on_delete=models.CASCADE, 
        related_name='certifications'
    )
    name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    credential_id = models.CharField(max_length=100, blank=True)
    credential_url = models.URLField(blank=True)
    certificate_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.freelancer.display_name} - {self.name}"

    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        return timezone.now().date() > self.expiry_date

    class Meta:
        ordering = ['-issue_date']
class BaseService(PolymorphicModel):
    """Enhanced base service model with improved start_working workflow"""
    
    SERVICE_TYPES = (
        ('software', 'Software'),
        ('research', 'Research'), 
        ('custom', 'Custom Service'),
        ('design', 'Design'),
        ('development', 'Development'),
        ('marketing', 'Marketing'),
        ('writing', 'Writing'),
        ('other', 'Other'),
    )

    # Enhanced status choices with clear workflow
    STATUS_CHOICES = (
        ('available', 'Available'),           # Initial state - open for bids
        ('assigned', 'Assigned'),             # Freelancer assigned (direct assignment)
        ('start_working', 'Start Working'),   # Ready to begin work (after approval/assignment)
        ('in_progress', 'In Progress'),       # Work has begun
        ('completed', 'Completed'),           # Work finished
        ('cancelled', 'Cancelled'),           # Order cancelled
        ('on_hold', 'On Hold'),              # Temporarily paused
        ('proceed_to_pay', 'Proceed to Pay'), # Ready for payment
    )

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    ACCEPTANCE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('returned', 'Returned'),
        ('completed', 'Completed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    # Core fields
    id = models.CharField(max_length=20, primary_key=True, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='services')
    title = models.CharField(max_length=255)
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Initial Budget/Cost estimate")
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Final approved bid amount")
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    
    # Status fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    acceptance_status = models.CharField(max_length=15, choices=ACCEPTANCE_STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Assignment fields
    assigned_to = models.ForeignKey(Freelancer, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_orders')
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    # Timing fields
    deadline = models.DateTimeField(blank=True, null=True)
    estimated_hours = models.IntegerField(blank=True, null=True)
    actual_hours = models.IntegerField(blank=True, null=True)
    
    # Requirements and additional info
    requirements = models.JSONField(default=list, help_text="List of requirements/skills needed")
    tags = models.JSONField(default=list, help_text="Tags for categorization")
    notes = models.TextField(blank=True, null=True, help_text="Internal admin notes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    ready_to_start_at = models.DateTimeField(null=True, blank=True)  # New field for start_working timestamp

    def save(self, *args, **kwargs):
        # Generate ID if not provided
        if not self.id:
            self.id = self.generate_order_id()
            
        # Auto-update timestamps based on status
        if self.status == 'start_working' and not self.ready_to_start_at:
            self.ready_to_start_at = timezone.now()
        elif self.status == 'in_progress' and not self.started_at:
            self.started_at = timezone.now()
        elif self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            
        # Update assignment timestamp
        if self.assigned_to and not self.assigned_at:
            self.assigned_at = timezone.now()
        elif not self.assigned_to:
            self.assigned_at = None
            
        super().save(*args, **kwargs)

    def clean(self):
        """Validate status transitions"""
        if self.pk:  # Only validate for existing objects
            old_instance = BaseService.objects.get(pk=self.pk)
            old_status = old_instance.status
            new_status = self.status
            
            # Define valid status transitions
            valid_transitions = {
                'available': ['assigned', 'cancelled'],
                'assigned': ['start_working', 'available', 'cancelled', 'on_hold'],
                'start_working': ['in_progress', 'on_hold', 'cancelled'],
                'in_progress': ['completed', 'on_hold', 'cancelled'],
                'completed': ['proceed_to_pay'],
                'cancelled': [],  # Terminal state
                'on_hold': ['start_working', 'in_progress', 'cancelled'],
                'proceed_to_pay': ['completed'],  # Can go back if payment fails
            }
            
            if old_status != new_status and new_status not in valid_transitions.get(old_status, []):
                raise ValidationError(
                    f"Invalid status transition from '{old_status}' to '{new_status}'"
                )

    def generate_order_id(self):
        """Generate unique order ID"""
        last_order = BaseService.objects.filter(id__startswith='ORD-').order_by('-id').first()
        if last_order:
            try:
                last_num = int(last_order.id.split('-')[1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        return f"ORD-{new_num:03d}"

    @property
    def client_id(self):
        """Generate client ID from user"""
        return f"CLIENT-{self.user.id:03d}"

    @property
    def assigned_to_name(self):
        """Get assigned freelancer name"""
        return self.assigned_to.name if self.assigned_to else None

    @property
    def final_cost(self):
        """Get the final cost - bid amount if available, otherwise initial cost"""
        return self.bid_amount if self.bid_amount is not None else self.cost

    @property
    def is_overdue(self):
        if self.deadline is None:
            return False
        return timezone.now() > self.deadline and self.status not in ['completed', 'cancelled']

    @property
    def time_remaining(self):
        """Get time remaining until deadline"""
        if self.status in ['completed', 'cancelled']:
            return None
        if self.deadline is None:
            return None
        delta = self.deadline - timezone.now()
        return delta if delta.total_seconds() > 0 else None

    @property
    def can_start_work(self):
        """Check if freelancer can start work"""
        return self.status == 'start_working' and self.assigned_to is not None

    @property
    def is_ready_to_start(self):
        """Check if order is in start_working status"""
        return self.status == 'start_working'

    def assign_to_freelancer(self, freelancer, bid_amount=None):
        """Assign order to a freelancer and set to start_working"""
        self.assigned_to = freelancer
        self.status = 'start_working'
        self.assigned_at = timezone.now()
        self.ready_to_start_at = timezone.now()
        
        # Update bid amount if provided (for direct assignments with negotiated price)
        if bid_amount is not None:
            self.bid_amount = bid_amount
            
        self.save()

    def approve_bid_and_assign(self, bid):
        """Approve a bid and assign the freelancer"""
        self.assigned_to = bid.freelancer
        self.bid_amount = bid.bid_amount  # This updates the bid_amount field in BaseService
        self.estimated_hours = bid.estimated_hours
        self.status = 'start_working'
        self.assigned_at = timezone.now()
        self.ready_to_start_at = timezone.now()
        
        # Update bid status
        bid.status = 'approved'
        bid.approved_at = timezone.now()
        bid.save()
        
        # Reject other bids for this order
        other_bids = self.bids.exclude(id=bid.id)
        other_bids.update(status='rejected')
        
        self.save()

    def start_work(self):
        """Freelancer starts working (transition from start_working to in_progress)"""
        if self.status != 'start_working':
            raise ValidationError("Can only start work from 'start_working' status")
        
        self.status = 'in_progress'
        if not self.started_at:
            self.started_at = timezone.now()
        self.save()

    def make_available(self):
        """Make order available (unassign and clear bid amount)"""
        self.assigned_to = None
        self.assigned_at = None
        self.ready_to_start_at = None
        self.bid_amount = None  # Clear the approved bid amount
        self.status = 'available'
        self.save()

    def put_on_hold(self):
        """Put order on hold"""
        self.status = 'on_hold'
        self.save()

    def cancel_order(self):
        """Cancel the order"""
        self.status = 'cancelled'
        self.save()

    def complete_order(self):
        """Mark order as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.id}: {self.title}"

    class Meta:
        ordering = ['-created_at']

# Keep existing specialized service models unchanged
class SoftwareService(BaseService):
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
        self.service_type = 'development'
        super().save(*args, **kwargs)

class ResearchService(BaseService):
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
    study_level = models.CharField(max_length=20, choices=STUDY_LEVEL_CHOICES, default='Undergraduate')

    def save(self, *args, **kwargs):
        self.service_type = 'writing'
        super().save(*args, **kwargs)

class CustomService(BaseService):
    sizes = models.JSONField(default=dict)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    delivery_time = models.CharField(max_length=100)
    support_duration = models.CharField(max_length=100)
    features = models.JSONField(default=list)
    process_link = models.URLField(blank=True, null=True)
    service_id = models.CharField(max_length=100, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.service_type = 'custom'
        super().save(*args, **kwargs)

class ServiceFile(models.Model):
    FILE_TYPES = (
        ('requirement', 'Requirement Document'),
        ('design', 'Design File'),
        ('source_code', 'Source Code'),
        ('documentation', 'Documentation'),
        ('deliverable', 'Deliverable'),
        ('other', 'Other'),
    )
    
    service = models.ForeignKey(BaseService, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="service_files/")
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='other')
    description = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.BigIntegerField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, 'size'):
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service.title} - {self.file.name}"

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(BaseService, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.order.id}: {self.previous_status} -> {self.new_status}"

    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = "Order Status Histories"

class OrderComment(models.Model):
    order = models.ForeignKey(BaseService, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Internal admin note vs client communication")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment on {self.order.id} by {self.author.username}"

    class Meta:
        ordering = ['-created_at']

class Bid(models.Model):
    BID_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    order = models.ForeignKey(BaseService, on_delete=models.CASCADE, related_name='bids')
    freelancer = models.ForeignKey(Freelancer, on_delete=models.CASCADE, related_name='bids')
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_hours = models.IntegerField()
    proposal = models.TextField()
    status = models.CharField(max_length=10, choices=BID_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_bids'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('order', 'freelancer')
        ordering = ['-created_at']

    def __str__(self):
        return f"Bid for order {self.order_id}"

    def approve(self, approved_by_user):
        """Approve this bid and assign the order to the freelancer"""
        self.order.approve_bid_and_assign(self)
        self.approved_by = approved_by_user
        self.save()

class BidFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    freelancer = django_filters.CharFilter(field_name='freelancer__id')
    order = django_filters.CharFilter(field_name='order__id')
    
    class Meta:
        model = Bid
        fields = ['status', 'freelancer', 'order']