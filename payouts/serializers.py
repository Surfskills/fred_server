# payouts/serializers.py
from rest_framework import serializers
from django.db.transaction import atomic
from django.utils import timezone
from django.db.models import Q

from authentication.models import Profile
from uni_services.models import Freelancer

from .models import Payout, PayoutSetting, Earnings
from django.db import transaction
import re
import json

class BasePayoutSerializer(serializers.ModelSerializer):
    """Base serializer with common payout fields"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    processed_by_name = serializers.SerializerMethodField()
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    
    class Meta:
        model = Payout
        fields = ['id', 'status', 'partner', 'status_display', 'payment_method', 'partner_name', 
                 'payment_method_display', 'amount', 'request_date', 'processed_date', 
                 'processed_by', 'processed_by_name', 'note', 'client_notes', 
                 'transaction_id', 'updated_at']
        read_only_fields = ['id', 'request_date', 'processed_date', 'updated_at']

    def get_processed_by_name(self, obj):
        if obj.processed_by:
            return f"{obj.processed_by.first_name} {obj.processed_by.last_name}".strip() or obj.processed_by.username
        return None


class FreelancerProfileSerializer(serializers.ModelSerializer):
    """Serializer for Freelancer profile details"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
   
        model = Freelancer
        fields = [
            'id', 'display_name', 'bio', 'title', 'freelancer_type', 
            'experience_level', 'skills', 'hourly_rate', 'location',
            'timezone', 'average_rating', 'total_projects_completed',
            'user_email', 'user_full_name', 'user_phone'
        ]


class PayoutSerializer(BasePayoutSerializer):
    """Serializer for payout read operations"""
    partner_details = serializers.SerializerMethodField()
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    earnings = serializers.SerializerMethodField()
    
    class Meta(BasePayoutSerializer.Meta):
        fields = BasePayoutSerializer.Meta.fields + ['partner_details', 'partner_name', 'earnings']

    def get_partner_details(self, obj):
        """Get partner details - assuming partner is a Freelancer instance"""
        if obj.partner:
            return FreelancerProfileSerializer(obj.partner).data
        return None

    def get_earnings(self, obj):
        """Get earnings associated with this payout"""
        earnings = obj.earnings_included.all()
        return EarningsSerializer(earnings, many=True).data


class PayoutCreateSerializer(BasePayoutSerializer):
    """Serializer for payout creation"""
    earnings_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of earnings IDs to include in this payout"
    )
    partner = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.all(),  # Add this line
        required=False  # This makes the field optional in the serializer
    )

    payment_details = serializers.JSONField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Import here to avoid circular imports
        from .models import Freelancer
        self.fields['partner'].queryset = Freelancer.objects.all()

    class Meta(BasePayoutSerializer.Meta):
        fields = BasePayoutSerializer.Meta.fields + ['partner', 'payment_details', 'earnings_ids']
        read_only_fields = BasePayoutSerializer.Meta.read_only_fields + ['status']

    def validate(self, data):
        request = self.context.get('request')
        
        # For non-staff users, automatically set their freelancer profile
        if request and not request.user.is_staff:
            if not hasattr(request.user, 'freelancer_profile'):
                raise serializers.ValidationError(
                    "User does not have an associated freelancer profile",
                    code='no_freelancer_profile'
                )
            data['partner'] = request.user.freelancer_profile
        
        # For staff users, partner is required if not provided
        elif request and request.user.is_staff and 'partner' not in data:
            raise serializers.ValidationError(
                "Partner ID is required for staff users",
                code='partner_required'
            )
        
        return data

    def validate_earnings_ids(self, value):
        """Validate that earnings exist and are available for payout"""
        if not value:
            return value
            
        earnings = Earnings.objects.filter(
            id__in=value,
            status='available'
        )
        
        if earnings.count() != len(value):
            unavailable_ids = set(value) - set(earnings.values_list('id', flat=True))
            raise serializers.ValidationError(
                f"The following earnings are not available for payout: {list(unavailable_ids)}"
            )
        
        return value

    @atomic
    def create(self, validated_data):
        earnings_ids = validated_data.pop('earnings_ids', [])
        
        # Create the Payout
        payout = Payout.objects.create(**validated_data)

        # Process earnings if provided
        if earnings_ids:
            earnings = Earnings.objects.filter(
                id__in=earnings_ids,
                status='available'
            )

            total_amount = 0
            for earning in earnings:
                earning.mark_as_processing(payout)
                total_amount += earning.amount

            payout.amount = total_amount
            payout.save()

        return payout

    def validate_payment_details(self, value):
        payment_method = self.initial_data.get('payment_method')
        required_fields = {
            'bank': ['account_number', 'bank_name'],
            'mpesa': ['phone_number'],
            'paypal': ['email'],
            'stripe': ['account_id']
        }

        if payment_method in required_fields:
            missing = [field for field in required_fields[payment_method] if not value.get(field)]
            if missing:
                raise serializers.ValidationError(
                    f"Missing required fields for {payment_method}: {', '.join(missing)}"
                )
        
        return value


class PayoutUpdateSerializer(BasePayoutSerializer):
    """Serializer for payout updates"""
    class Meta(BasePayoutSerializer.Meta):
        fields = BasePayoutSerializer.Meta.fields + ['transaction_id']

    def update(self, instance, validated_data):
        request = self.context.get('request')
        
        # Track if status is being changed to COMPLETED
        completing_payout = (
            'status' in validated_data and 
            validated_data['status'] == Payout.Status.COMPLETED and
            instance.status != Payout.Status.COMPLETED
        )
        
        if 'status' in validated_data and validated_data['status'] != instance.status:
            validated_data['processed_by'] = request.user if request else None
            
            if validated_data['status'] == Payout.Status.COMPLETED:
                validated_data['processed_date'] = timezone.now()
                
        # Update the instance
        try:
            with transaction.atomic():
                instance = super().update(instance, validated_data)
                
                # After updating, if status changed to COMPLETED, update earnings
                if completing_payout:
                    instance._update_associated_earnings()
        except Exception as e:
            raise
            
        return instance


class PayoutSettingSerializer(serializers.ModelSerializer):
    """Serializer for payout settings"""
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    schedule_display = serializers.CharField(source='get_payout_schedule_display', read_only=True)
    payment_details = serializers.SerializerMethodField()
    partner_name = serializers.CharField(source='partner.name', read_only=True)

    class Meta:
        model = PayoutSetting
        fields = '__all__'
        read_only_fields = ['updated_at']

    def get_payment_details(self, obj):
        """Ensure payment_details is always returned as a dict with proper formatting"""
        if not obj.payment_details:
            return {}
        
        # If payment_details is already a dict, return it as-is
        if isinstance(obj.payment_details, dict):
            return obj.payment_details
        
        # If it's stored as a string, try to parse it as JSON
        try:
            return json.loads(obj.payment_details)
        except (TypeError, json.JSONDecodeError):
            return {}

    def validate_payment_details(self, value):
        # Normalize keys to snake_case if they came in camelCase
        def camel_to_snake(s): return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()
        value = {camel_to_snake(k): v for k, v in value.items()}

        payment_method = self.initial_data.get('payment_method')
        if not payment_method:
            raise serializers.ValidationError("Payment method must be specified.")

        if payment_method == 'paypal':
            if not value.get('email'):
                raise serializers.ValidationError("Paypal email is required.")
        elif payment_method == 'bank':
            required_fields = ['account_name', 'account_number', 'routing_number', 'bank_name']
            for field in required_fields:
                if not value.get(field):
                    raise serializers.ValidationError(f"Bank details require the field: {field}.")
        elif payment_method == 'mpesa':
            if not value.get('phone_number'):
                raise serializers.ValidationError("M-Pesa requires a phone number.")
        elif payment_method == 'stripe':
            if not value.get('account_id'):
                raise serializers.ValidationError("Stripe requires an account ID.")
        else:
            raise serializers.ValidationError(f"Unsupported payment method: {payment_method}")

        return value


class BaseEarningsSerializer(serializers.ModelSerializer):
    """Base serializer with common earnings fields"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    payout_id = serializers.CharField(source='payout.id', read_only=True)
    status = serializers.CharField(read_only=True)
    raw_status = serializers.CharField(source='status', read_only=True)
    approved_by = serializers.CharField(source='approved_by.username', read_only=True)
    rejected_by = serializers.CharField(source='rejected_by.username', read_only=True)

    class Meta:
        model = Earnings
        fields = [
            'id', 'amount', 'date', 'source', 'paid_date', 'source_display',
            'status', 'raw_status', 'status_display', 'notes',
            'created_at', 'updated_at', 'payout_id',
            'approved_by', 'approval_date', 'rejected_by', 'rejection_date'
        ]
        read_only_fields = [
            'created_at', 'updated_at',
            'approved_by', 'approval_date',
            'rejected_by', 'rejection_date'
        ]


class EarningsSerializer(BaseEarningsSerializer):
    """Serializer for earnings read operations"""
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    project_details = serializers.SerializerMethodField()

    class Meta(BaseEarningsSerializer.Meta):
        fields = BaseEarningsSerializer.Meta.fields + ['partner_name', 'project_details']

    def get_project_details(self, obj):
        """Get project/order details if earnings are from project completion"""
        # This would depend on your project/order model structure
        # You might want to add a project field to the Earnings model
        if hasattr(obj, 'project') and obj.project:
            return {
                'id': obj.project.id,
                'title': obj.project.title,
                'status': obj.project.status
            }
        return None


class EarningsCreateSerializer(BaseEarningsSerializer):
    """Serializer for earnings creation"""

    class Meta(BaseEarningsSerializer.Meta):
        fields = BaseEarningsSerializer.Meta.fields + ['partner']
        read_only_fields = BaseEarningsSerializer.Meta.read_only_fields

    def validate(self, data):
        """Enhanced validation to ensure proper status assignment based on source"""
        # Set default date if not provided
        if not data.get('date'):
            data['date'] = timezone.now().date()
        
        # Make sure source is set, defaulting to PROJECT if not specified
        source = data.get('source', Earnings.Source.PROJECT)
        data['source'] = source
        
        return data


class EarningsUpdateSerializer(serializers.ModelSerializer):
    """Serializer for earnings updates"""
    
    class Meta:
        model = Earnings
        fields = ['notes']
        
    def validate(self, data):
        """Prevent unauthorized status changes"""
        # Status changes should only happen through dedicated endpoints like 
        # approve(), reject(), mark_paid(), etc.
        if 'status' in self.initial_data:
            raise serializers.ValidationError(
                "Status cannot be directly changed. Use the appropriate endpoint instead."
            )
        return data