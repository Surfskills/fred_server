from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    # Specify the fields to display in the list view
    list_display = ('email', 'is_staff', 'is_active', 'created_at')
    
    # Fields to search by
    search_fields = ('email',)
    
    # Filters in the list view
    list_filter = ('is_staff', 'is_active')
    
    # Fieldsets for the user edit page
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('created_at',)}),
    )

    # Fields to display when adding a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )

    # Define ordering
    ordering = ('email',)  # Order by email instead of username

    model = User

# Register the CustomUserAdmin class with the User model
admin.site.register(User, CustomUserAdmin)
