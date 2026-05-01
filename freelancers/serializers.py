from decimal import Decimal
from rest_framework import serializers

from uni_services.models import Freelancer, FreelancerCertification, FreelancerPortfolio, FreelancerReview


class FreelancerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Freelancer
        fields = [
            'id',
            'display_name',
            'title',
            'freelancer_type',
            'marketplace_tier',
            'experience_level',
            'is_available',
            'availability_status',
            'hourly_rate',
            'location',
            'average_rating',
            'total_projects_completed',
            'profile_completion_score',
            'is_profile_verified',
            'last_active',
        ]


class MarketplaceDirectorySerializer(serializers.ModelSerializer):
    """Public card payload: first name, photo, specialism, tier, catalog titles."""
    public_first_name = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    catalog_preview = serializers.SerializerMethodField()
    skill_preview = serializers.SerializerMethodField()
    marketplace_tier_display = serializers.CharField(source='get_marketplace_tier_display', read_only=True)

    class Meta:
        model = Freelancer
        fields = [
            'id',
            'public_first_name',
            'title',
            'experience_level',
            'marketplace_tier',
            'marketplace_tier_display',
            'profile_photo',
            'skill_preview',
            'catalog_preview',
            'average_rating',
            'hourly_rate',
        ]

    def get_public_first_name(self, obj):
        if getattr(obj.user, 'first_name', None):
            return obj.user.first_name
        name = (obj.display_name or '').strip()
        return name.split()[0] if name else 'Freelancer'

    def get_profile_photo(self, obj):
        pic = getattr(obj.user, 'profile_picture', None)
        if pic and getattr(pic, 'name', None):
            request = self.context.get('request')
            url = pic.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None

    def get_catalog_preview(self, obj):
        return list(obj.portfolio_items.values_list('title', flat=True)[:5])

    def get_skill_preview(self, obj):
        raw = obj.skills if isinstance(obj.skills, list) else []
        out = [str(s).strip() for s in raw if str(s).strip()]
        return out[:6]

class FreelancerDetailSerializer(serializers.ModelSerializer):
    skills = serializers.SerializerMethodField()
    specializations = serializers.SerializerMethodField()
    languages = serializers.SerializerMethodField()
    
    class Meta:
        model = Freelancer
        fields = [
            'id',
            'display_name',
            'title',
            'bio',
            'freelancer_type',
            'marketplace_tier',
            'experience_level',
            'is_available',
            'availability_status',
            'hourly_rate',
            'minimum_project_budget',
            'preferred_project_duration',
            'max_concurrent_projects',
            'location',
            'timezone',
            'willing_to_travel',
            'portfolio_url',
            'skills',
            'specializations',
            'languages',
            'average_rating',
            'total_projects_completed',
            'total_earnings',
            'profile_completion_score',
            'is_profile_verified',
            'is_featured',
            'created_at',
            'updated_at',
            'last_active',
        ]
    
    def get_skills(self, obj):
        return obj.skills
    
    def get_specializations(self, obj):
        return obj.specializations
    
    def get_languages(self, obj):
        return obj.languages

class FreelancerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Freelancer
        fields = [
            'user',
            'display_name',
            'title',
            'bio',
            'freelancer_type',
            'experience_level',
            'hourly_rate',
            'minimum_project_budget',
            'location',
            'timezone',
            'skills',
            'specializations',
            'languages',
        ]

class FreelancerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Freelancer
        fields = [
            'display_name',
            'title',
            'bio',
            'freelancer_type',
            'experience_level',
            'hourly_rate',
            'minimum_project_budget',
            'preferred_project_duration',
            'max_concurrent_projects',
            'willing_to_travel',
            'location',
            'timezone',
            'skills',
            'specializations',
            'languages',
            'portfolio_url',
            'is_available',
            'availability_status',
            'is_profile_verified',
            'is_featured',
        ]

class FreelancerStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Freelancer
        fields = ['is_available', 'availability_status']


class SetMarketplaceTierSerializer(serializers.Serializer):
    """Self-service: set or upgrade marketplace_tier (single track per freelancer)."""

    marketplace_tier = serializers.ChoiceField(choices=Freelancer.MARKETPLACE_TIER_CHOICES)

class FreelancerSearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=False)
    freelancer_types = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    min_rating = serializers.FloatField(required=False, min_value=0, max_value=5)
    max_rate = serializers.DecimalField(max_digits=10, decimal_places=2, max_value=Decimal('1000.00')  )
    min_projects = serializers.IntegerField(required=False, min_value=0)
    available_only = serializers.BooleanField(required=False, default=False)
    verified_only = serializers.BooleanField(required=False, default=False)

from decimal import Decimal
from rest_framework import serializers

class FreelancerStatsSerializer(serializers.Serializer):
    total_freelancers = serializers.IntegerField(min_value=0)
    available_freelancers = serializers.IntegerField(min_value=0)
    busy_freelancers = serializers.IntegerField(min_value=0)
    new_freelancers = serializers.IntegerField(min_value=0)
    verified_freelancers = serializers.IntegerField(min_value=0)
    average_rating = serializers.FloatField(
        min_value=Decimal('0.0'),  # Changed to Decimal
        max_value=Decimal('5.0')   # Changed to Decimal
    )
    average_rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.0')  # Explicit min value
    )
    freelancers_by_type = serializers.DictField()
    freelancers_by_experience = serializers.DictField()
    experience_distribution = serializers.ListField()
    top_skills = serializers.ListField()

    # Removed the duplicate average_rating field

class FreelancerPortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = FreelancerPortfolio
        fields = [
            'id',
            'title',
            'description',
            'project_url',
            'image',
            'technologies_used',
            'project_type',
            'completion_date',
            'client_name',
            'is_featured',
            'created_at',
        ]

class FreelancerReviewSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    client_email = serializers.SerializerMethodField()
    
    class Meta:
        model = FreelancerReview
        fields = [
            'id',
            'client',
            'client_name',
            'client_email',
            'order',
            'rating',
            'review_text',
            'communication_rating',
            'quality_rating',
            'timeliness_rating',
            'would_recommend',
            'created_at',
        ]
        read_only_fields = ['client', 'freelancer', 'order']
    
    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.email

    def get_client_email(self, obj):
        return obj.client.email

class FreelancerCertificationSerializer(serializers.ModelSerializer):
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = FreelancerCertification
        fields = [
            'id',
            'name',
            'issuing_organization',
            'issue_date',
            'expiry_date',
            'is_expired',
            'credential_id',
            'credential_url',
            'certificate_file',
            'is_verified',
            'created_at',
        ]
    
    def get_is_expired(self, obj):
        return obj.is_expired