from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta

from uni_services.models import (
    Freelancer, 
    FreelancerCertification, 
    FreelancerPortfolio, 
    FreelancerReview
)


class FreelancerPortfolioInline(admin.TabularInline):
    model = FreelancerPortfolio
    extra = 0
    fields = ('title', 'project_type', 'project_url', 'is_featured', 'completion_date')
    readonly_fields = ('created_at',)


class FreelancerCertificationInline(admin.TabularInline):
    model = FreelancerCertification
    extra = 0
    fields = ('name', 'issuing_organization', 'issue_date', 'expiry_date', 'is_verified')
    readonly_fields = ('created_at', 'is_expired')


class FreelancerReviewInline(admin.TabularInline):
    model = FreelancerReview
    extra = 0
    fields = ('client', 'rating', 'review_text', 'would_recommend', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Freelancer)
class FreelancerAdmin(admin.ModelAdmin):
    list_display = [
        'display_name',
        'user_email',
        'freelancer_type',
        'experience_level',
        'availability_badge',
        'hourly_rate',
        'rating_display',
        'total_projects_completed',
        'verification_status',
        'last_active_display',
        'profile_completion_bar'
    ]
    
    list_filter = [
        'freelancer_type',
        'experience_level',
        'is_available',
        'availability_status',
        'is_profile_verified',
        'is_featured',
        'created_at',
        'last_active',
    ]
    
    search_fields = [
        'display_name',
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'title',
        'bio',
        'location',
        'skills',
        'specializations',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'total_earnings',
        'average_rating',
        'total_projects_completed',
        'profile_completion_score',
        'last_active',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'user',
                'display_name',
                'title',
                'bio',
            )
        }),
        ('Professional Details', {
            'fields': (
                'freelancer_type',
                'experience_level',
                'skills',
                'specializations',
                'languages',
            )
        }),
        ('Availability & Rates', {
            'fields': (
                'is_available',
                'availability_status',
                'hourly_rate',
                'minimum_project_budget',
                'preferred_project_duration',
                'max_concurrent_projects',
            )
        }),
        ('Location & Travel', {
            'fields': (
                'location',
                'timezone',
                'willing_to_travel',
            )
        }),
        ('Portfolio & Links', {
            'fields': (
                'portfolio_url',
            )
        }),
        ('Status & Verification', {
            'fields': (
                'is_profile_verified',
                'is_featured',
                'profile_completion_score',
            )
        }),
        ('Statistics (Read-only)', {
            'fields': (
                'average_rating',
                'total_projects_completed',
                'total_earnings',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps (Read-only)', {
            'fields': (
                'created_at',
                'updated_at',
                'last_active',
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [FreelancerPortfolioInline, FreelancerCertificationInline, FreelancerReviewInline]
    
    actions = [
        'mark_as_verified',
        'mark_as_unverified',
        'mark_as_featured',
        'mark_as_unfeatured',
        'mark_as_available',
        'mark_as_unavailable',
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'
    
    def availability_badge(self, obj):
        if obj.is_available:
            color = 'green' if obj.availability_status == 'available' else 'orange'
            status = obj.get_availability_status_display()
        else:
            color = 'red'
            status = 'Unavailable'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )
    availability_badge.short_description = 'Availability'
    availability_badge.admin_order_field = 'is_available'
    
    def rating_display(self, obj):
        if obj.average_rating:
            stars = '★' * int(obj.average_rating) + '☆' * (5 - int(obj.average_rating))
            return format_html(
                '<span title="{}/5.0">{}</span>',
                obj.average_rating,
                stars
            )
        return 'No ratings'
    rating_display.short_description = 'Rating'
    rating_display.admin_order_field = 'average_rating'
    
    def verification_status(self, obj):
        if obj.is_profile_verified:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Unverified</span>'
        )
    verification_status.short_description = 'Verification'
    verification_status.admin_order_field = 'is_profile_verified'
    
    def last_active_display(self, obj):
        if obj.last_active:
            now = timezone.now()
            diff = now - obj.last_active
            
            if diff < timedelta(hours=1):
                return format_html('<span style="color: green;">Online</span>')
            elif diff < timedelta(days=1):
                return format_html('<span style="color: orange;">Today</span>')
            elif diff < timedelta(days=7):
                return format_html('<span style="color: orange;">{} days ago</span>', diff.days)
            else:
                return format_html('<span style="color: red;">{} days ago</span>', diff.days)
        return 'Never'
    last_active_display.short_description = 'Last Active'
    last_active_display.admin_order_field = 'last_active'
    
    def profile_completion_bar(self, obj):
        percentage = obj.profile_completion_score or 0
        color = 'green' if percentage >= 80 else 'orange' if percentage >= 50 else 'red'
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{}%</div></div>',
            percentage,
            color,
            percentage
        )
    profile_completion_bar.short_description = 'Profile Completion'
    profile_completion_bar.admin_order_field = 'profile_completion_score'
    
    # Actions
    def mark_as_verified(self, request, queryset):
        updated = queryset.update(is_profile_verified=True)
        self.message_user(request, f'{updated} freelancers marked as verified.')
    mark_as_verified.short_description = 'Mark selected freelancers as verified'
    
    def mark_as_unverified(self, request, queryset):
        updated = queryset.update(is_profile_verified=False)
        self.message_user(request, f'{updated} freelancers marked as unverified.')
    mark_as_unverified.short_description = 'Mark selected freelancers as unverified'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} freelancers marked as featured.')
    mark_as_featured.short_description = 'Mark selected freelancers as featured'
    
    def mark_as_unfeatured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} freelancers removed from featured.')
    mark_as_unfeatured.short_description = 'Remove selected freelancers from featured'
    
    def mark_as_available(self, request, queryset):
        updated = queryset.update(is_available=True, availability_status='available')
        self.message_user(request, f'{updated} freelancers marked as available.')
    mark_as_available.short_description = 'Mark selected freelancers as available'
    
    def mark_as_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False, availability_status='unavailable')
        self.message_user(request, f'{updated} freelancers marked as unavailable.')
    mark_as_unavailable.short_description = 'Mark selected freelancers as unavailable'


@admin.register(FreelancerPortfolio)
class FreelancerPortfolioAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'freelancer_name',
        'project_type',
        'completion_date',
        'is_featured',
        'has_image',
        'has_url',
        'created_at'
    ]
    
    list_filter = [
        'project_type',
        'is_featured',
        'completion_date',
        'created_at',
    ]
    
    search_fields = [
        'title',
        'description',
        'freelancer__display_name',
        'freelancer__user__username',
        'client_name',
        'technologies_used',
    ]
    
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Project Information', {
            'fields': (
                'freelancer',
                'title',
                'description',
                'project_type',
                'completion_date',
                'client_name',
            )
        }),
        ('Media & Links', {
            'fields': (
                'project_url',
                'image',
            )
        }),
        ('Technical Details', {
            'fields': (
                'technologies_used',
            )
        }),
        ('Status', {
            'fields': (
                'is_featured',
                'created_at',
            )
        }),
    )
    
    def freelancer_name(self, obj):
        return obj.freelancer.display_name
    freelancer_name.short_description = 'Freelancer'
    freelancer_name.admin_order_field = 'freelancer__display_name'
    
    def has_image(self, obj):
        return format_html(
            '<span style="color: {};">●</span>',
            'green' if obj.image else 'red'
        )
    has_image.short_description = 'Image'
    
    def has_url(self, obj):
        return format_html(
            '<span style="color: {};">●</span>',
            'green' if obj.project_url else 'red'
        )
    has_url.short_description = 'URL'


@admin.register(FreelancerReview)
class FreelancerReviewAdmin(admin.ModelAdmin):
    list_display = [
        'freelancer_name',
        'client_name',
        'rating_stars',
        'communication_rating',
        'quality_rating',
        'timeliness_rating',
        'would_recommend',
        'created_at'
    ]
    
    list_filter = [
        'rating',
        'communication_rating',
        'quality_rating',
        'timeliness_rating',
        'would_recommend',
        'created_at',
    ]
    
    search_fields = [
        'freelancer__display_name',
        'freelancer__user__username',
        'client__username',
        'client__email',
        'client__first_name',
        'client__last_name',
        'review_text',
    ]
    
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Review Information', {
            'fields': (
                'freelancer',
                'client',
                'order',
                'review_text',
            )
        }),
        ('Ratings', {
            'fields': (
                'rating',
                'communication_rating',
                'quality_rating',
                'timeliness_rating',
                'would_recommend',
            )
        }),
        ('Timestamp', {
            'fields': (
                'created_at',
            )
        }),
    )
    
    def freelancer_name(self, obj):
        return obj.freelancer.display_name
    freelancer_name.short_description = 'Freelancer'
    freelancer_name.admin_order_field = 'freelancer__display_name'
    
    def client_name(self, obj):
        return obj.client.get_full_name() or obj.client.username
    client_name.short_description = 'Client'
    client_name.admin_order_field = 'client__username'
    
    def rating_stars(self, obj):
        stars = '★' * int(obj.rating) + '☆' * (5 - int(obj.rating))
        return format_html(
            '<span title="{}/5">{}</span>',
            obj.rating,
            stars
        )
    rating_stars.short_description = 'Overall Rating'
    rating_stars.admin_order_field = 'rating'

