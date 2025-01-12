# authentication/models.py

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

# User Manager class
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        
        # Ensure user_type is provided, default to 'CLIENT' if not
        user_type = extra_fields.get('user_type', User.Types.CLIENT)
        
        # Create the user instance
        user = self.model(email=email, user_type=user_type, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', User.Types.ADMIN)  # Superuser should be an admin
        
        return self.create_user(email, password, **extra_fields)
    
    def create_client(self, email, password=None, **extra_fields):
        extra_fields.setdefault('user_type', User.Types.CLIENT)  # Ensure client type
        return self.create_user(email, password, **extra_fields)
    
    def create_admin(self, email, password=None, **extra_fields):
        extra_fields.setdefault('user_type', User.Types.ADMIN)  # Ensure admin type
        extra_fields.setdefault('is_staff', True)  # Admin should be staff
        return self.create_user(email, password, **extra_fields)

# User model definition
class User(AbstractBaseUser, PermissionsMixin):
    class Types(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        CLIENT = "CLIENT", "Client"

    # Base fields
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # User type field (optional, defaults to CLIENT)
    user_type = models.CharField(
        max_length=10,
        choices=Types.choices,
        default=Types.CLIENT
    )
    
    # Additional fields (all optional)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Only email and password are required

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self):
        return self.user_type == self.Types.ADMIN

    @property
    def is_client(self):
        return self.user_type == self.Types.CLIENT


# Profile model for additional user data
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(max_length=200, blank=True)
    company = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s profile"
