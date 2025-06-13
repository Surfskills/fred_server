# Updated User model with fixed calculate_profile_completion method

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import threading

# Thread-local storage for tracking profile completion calculations
_thread_locals = threading.local()

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        
        # Ensure user_type is provided, default to 'CLIENT' if not
        user_type = extra_fields.pop('user_type', User.Types.CLIENT)
        
        # Create the user instance with the correct fields
        user = self.model(email=email, user_type=user_type, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', User.Types.ADMIN)
        
        return self.create_user(email, password, **extra_fields)
    
    def create_client(self, email, password=None, **extra_fields):
        extra_fields.setdefault('user_type', User.Types.CLIENT)
        return self.create_user(email, password, **extra_fields)
    
    def create_admin(self, email, password=None, **extra_fields):
        extra_fields.setdefault('user_type', User.Types.ADMIN)
        extra_fields.setdefault('is_staff', True)
        return self.create_user(email, password, **extra_fields)
    
    def create_support_agent(self, email, password=None, **extra_fields):
        extra_fields.setdefault('user_type', User.Types.SUPPORT_AGENT)
        extra_fields.setdefault('is_staff', True)
        return self.create_user(email, password, **extra_fields)
    
    def create_freelancer(self, email, password=None, **extra_fields):
        extra_fields.setdefault('user_type', User.Types.FREELANCER)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Types(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        CLIENT = "CLIENT", "Client"
        SUPPORT_AGENT = "SUPPORT_AGENT", "Support Agent"
        FREELANCER = "FREELANCER", "Freelancer"

    # Base fields
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # User type field
    user_type = models.CharField(
        max_length=15,
        choices=Types.choices,
        default=Types.CLIENT
    )
    
    # Profile completion tracking
    is_profile_complete = models.BooleanField(default=False)
    profile_completion_percentage = models.IntegerField(default=0)
    
    # Basic profile fields
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self):
        """Get the best available name for display"""
        if self.full_name:
            return self.full_name
        return self.email.split('@')[0]

    @property
    def is_admin(self):
        return self.user_type == self.Types.ADMIN

    @property
    def is_client(self):
        return self.user_type == self.Types.CLIENT
    
    @property
    def is_support_agent(self):
        return self.user_type == self.Types.SUPPORT_AGENT
    
    @property
    def is_freelancer(self):
        return self.user_type == self.Types.FREELANCER

    def get_freelancer_profile(self):
        """Safe method to get freelancer profile"""
        if not self.is_freelancer:
            return None
        try:
            return self.freelancer_profile
        except:
            return None
    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()
    def calculate_profile_completion(self):
        """Calculate profile completion percentage - SAFE VERSION"""
        
        # Prevent recursion using thread-local storage
        if not hasattr(_thread_locals, 'calculating_completion'):
            _thread_locals.calculating_completion = set()
            
        completion_key = f"user_{self.pk}"
        if completion_key in _thread_locals.calculating_completion:
            return self.profile_completion_percentage
            
        try:
            _thread_locals.calculating_completion.add(completion_key)
            
            completion = 0
            total_fields = 0
            
            # Basic fields (20% each)
            basic_fields = [
                self.first_name,
                self.last_name,
                self.phone_number,
                bool(self.profile_picture),
            ]
            
            for field in basic_fields:
                total_fields += 1
                if field:
                    completion += 1
            
            # Type-specific completion
            if self.is_freelancer:
                try:
                    freelancer_profile = self.get_freelancer_profile()
                    if freelancer_profile:
                        # Simplified check to avoid complex queries
                        freelancer_fields = [
                            bool(freelancer_profile.bio),
                            bool(getattr(freelancer_profile, 'hourly_rate', None)),
                        ]
                        
                        for field in freelancer_fields:
                            total_fields += 1
                            if field:
                                completion += 1
                except Exception as e:
                    # Log the error and continue without freelancer-specific completion
                    print(f"Error calculating freelancer completion: {e}")
                    pass
            
            percentage = int((completion / total_fields) * 100) if total_fields > 0 else 0
            
            # Update the fields using bulk update to avoid triggering signals
            # Don't call self.save() or self.refresh_from_db() here
            User.objects.filter(pk=self.pk).update(
                profile_completion_percentage=percentage,
                is_profile_complete=percentage >= 80,
            )
            
            # Update the current instance's values manually
            self.profile_completion_percentage = percentage
            self.is_profile_complete = percentage >= 80
            
            return percentage
            
        finally:
            _thread_locals.calculating_completion.discard(completion_key)

    def save(self, *args, **kwargs):
        # Don't automatically calculate profile completion on save
        # This will be handled by signals when needed
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]


# Enhanced Profile model (unchanged)
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(max_length=200, blank=True)
    company = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=50, blank=True)
    
    # Social links
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def name(self):
        """Get the user's full name from the associated User model"""
        return self.user.get_full_name() or self.user.email

    def __str__(self):
        return f"{self.name}'s profile"

    class Meta:
        indexes = [
            models.Index(fields=['location']),
        ]