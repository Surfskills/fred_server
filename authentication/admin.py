from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile

# Custom User Admin class to manage User model in the Django Admin
class CustomUserAdmin(UserAdmin):
    # Specify the fields to display in the list view
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active', 'created_at')

    # Fields to search by
    search_fields = ('email', 'first_name', 'last_name')

    # Filters in the list view
    list_filter = ('is_staff', 'is_active', 'user_type')

    # Fieldsets for the user edit page (this is the structure of the form when editing a user)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_type')}),
        ('Important dates', {'fields': ('created_at',)}),
    )

    # Fields to display when adding a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'phone_number', 'profile_picture', 'is_active', 'is_staff', 'is_superuser', 'user_type'),
        }),
    )

    # Define ordering (this will order users by email in the admin interface)
    ordering = ('email',)  # Order by email instead of username

    model = User

# Register the CustomUserAdmin class with the User model
admin.site.register(User, CustomUserAdmin)

# Profile Admin class to manage Profile model in the Django Admin
class ProfileAdmin(admin.ModelAdmin):
    # Specify the fields to display in the list view for profiles
    list_display = ('user', 'bio', 'location', 'company', 'created_at', 'updated_at')

    # Fields to search by in the profiles list
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'company')

    # Filters in the list view
    list_filter = ('created_at',)

    # Define ordering (this will order profiles by user email in the admin interface)
    ordering = ('user__email',)

    model = Profile

# Register the ProfileAdmin class with the Profile model
admin.site.register(Profile, ProfileAdmin)
