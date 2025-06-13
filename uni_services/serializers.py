# serializers.py - Updated to match enhanced models
from rest_framework import serializers
from django.utils import timezone

from authentication.models import User
from freelancers.serializers import FreelancerSerializer
from .models import (
    BaseService, Bid, SoftwareService, ResearchService, CustomService, 
    ServiceFile, Freelancer,
    OrderStatusHistory, OrderComment
)


# User Serializers
class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']


# Service File Serializers
class ServiceFileSerializer(serializers.ModelSerializer):
    uploaded_by = UserBasicSerializer(read_only=True)
    file_size_display = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)

    class Meta:
        model = ServiceFile
        fields = [
            'id', 'service', 'file', 'file_type', 'file_type_display', 'description', 
            'uploaded_by', 'uploaded_at', 'file_size', 'file_size_display', 'file_name'
        ]
        read_only_fields = ('uploaded_at', 'file_size', 'uploaded_by')

    def get_file_size_display(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return "N/A"

    def get_file_name(self, obj):
        return obj.file.name.split('/')[-1] if obj.file else 'N/A'


class ServiceFileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFile
        fields = ['file', 'file_type', 'description']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['uploaded_by'] = request.user
        return super().create(validated_data)


# Order Status History Serializers
class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = UserBasicSerializer(read_only=True)
    previous_status_display = serializers.SerializerMethodField()
    new_status_display = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'order', 'previous_status', 'previous_status_display', 
            'new_status', 'new_status_display', 'changed_by', 'changed_at', 'notes'
        ]
        read_only_fields = ('changed_at',)

    def get_previous_status_display(self, obj):
        if obj.previous_status:
            return dict(BaseService.STATUS_CHOICES).get(obj.previous_status, obj.previous_status)
        return None

    def get_new_status_display(self, obj):
        return dict(BaseService.STATUS_CHOICES).get(obj.new_status, obj.new_status)


# Order Comment Serializers
class OrderCommentSerializer(serializers.ModelSerializer):
    author = UserBasicSerializer(read_only=True)
    message_short = serializers.SerializerMethodField()

    class Meta:
        model = OrderComment
        fields = [
            'id', 'order', 'author', 'message', 'message_short', 
            'is_internal', 'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at')

    def get_message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message


class OrderCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderComment
        fields = ['message', 'is_internal']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['author'] = request.user
        return super().create(validated_data)

class BidForServiceSerializer(serializers.ModelSerializer):
    """Specialized bid serializer for service details - avoids circular import"""
    freelancer = FreelancerSerializer(read_only=True)
    freelancer_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    status_badge = serializers.SerializerMethodField()
    created_at_display = serializers.SerializerMethodField()
    proposal_short = serializers.SerializerMethodField()
    
    class Meta:
        model = Bid
        fields = [
            'id', 'freelancer', 'freelancer_info', 'bid_amount', 'estimated_hours', 
            'proposal', 'proposal_short', 'status', 'status_display', 'status_badge',
            'created_at', 'created_at_display', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at')
    
    def get_freelancer_info(self, obj):
        """Get essential freelancer information"""
        if not obj.freelancer:
            return None
        freelancer = obj.freelancer
        return {
            'id': freelancer.id,
            'name': freelancer.display_name,
            'email': freelancer.user.email,
            'freelancer_type': freelancer.freelancer_type,
            'freelancer_type_display': freelancer.get_freelancer_type_display(),
            'hourly_rate': freelancer.hourly_rate,
            'rating': freelancer.average_rating,
            'completed_projects': freelancer.total_projects_completed
        }
    
    def get_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'withdrawn': 'gray',
            'under_review': 'blue',
            'revision_requested': 'yellow'
        }
        return {
            'color': colors.get(obj.status, 'gray'),
            'text': obj.get_status_display()
        }
    
    def get_created_at_display(self, obj):
        return obj.created_at.strftime('%b %d, %Y %I:%M %p') if obj.created_at else None
    
    def get_proposal_short(self, obj):
        return obj.proposal[:150] + '...' if len(obj.proposal) > 150 else obj.proposal


# Enhanced Base Service Serializers
class BaseServiceSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    assigned_to = FreelancerSerializer(read_only=True)
    assigned_to_name = serializers.CharField(read_only=True)
    assigned_to_info = serializers.SerializerMethodField()
    client_id = serializers.CharField(read_only=True)
    client_info = serializers.SerializerMethodField()
    files = ServiceFileSerializer(many=True, read_only=True)
    files_count = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    time_remaining = serializers.SerializerMethodField()
    time_remaining_display = serializers.SerializerMethodField()
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    comments = OrderCommentSerializer(many=True, read_only=True)
    bids = BidForServiceSerializer(many=True, read_only=True)

    # Display fields
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    acceptance_status_display = serializers.CharField(source='get_acceptance_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    # Badges and calculated fields
    status_badge = serializers.SerializerMethodField()
    payment_status_badge = serializers.SerializerMethodField()
    priority_badge = serializers.SerializerMethodField()
    cost_display = serializers.SerializerMethodField()
    deadline_info = serializers.SerializerMethodField()
    title_short = serializers.SerializerMethodField()
    bid_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, allow_null=True, required=False)
    final_cost = serializers.SerializerMethodField()

    class Meta:
        model = BaseService
        fields = '__all__'  # include all model fields automatically
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'assigned_at', 'ready_to_start_at',
            'started_at', 'completed_at', 'user', 'client_id'
        )


    def get_final_cost(self, obj):
        """Get the final cost - bid amount if available, otherwise initial cost"""
        # Handle both None and zero values properly
        if obj.bid_amount is not None and obj.bid_amount > 0:
            return float(obj.bid_amount)  # Convert Decimal to float for JSON serialization
        elif obj.cost is not None:
            return float(obj.cost)
        return None  # Return None instead of 0 if no cost is set
    
    def get_final_cost_display(self, obj):
        """Get formatted final cost display"""
        final_cost = self.get_final_cost(obj)
        if final_cost is not None:
            return f'${final_cost:,.2f}'
        return 'N/A'
    
    def get_assigned_to_info(self, obj):
        if obj.assigned_to:
            return {
                'name': obj.assigned_to.display_name,
                'type': obj.assigned_to.freelancer_type,
                'display': f"{obj.assigned_to.display_name} ({obj.assigned_to.get_freelancer_type_display()})"
            }
        return {'display': 'Unassigned', 'color': 'red'}

    def get_client_info(self, obj):
        return {
            'email': obj.user.email,
            'client_id': obj.client_id,
            'name': f"{obj.user.first_name} {obj.user.last_name}"
        }

    def get_files_count(self, obj):
        return obj.files.count()

    def get_time_remaining(self, obj):
        time_remaining = obj.time_remaining
        if time_remaining:
            days = time_remaining.days
            hours, remainder = divmod(time_remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return "Expired" if obj.is_overdue else None

    def get_time_remaining_display(self, obj):
        time_remaining = obj.time_remaining
        if time_remaining:
            days = time_remaining.days
            hours, remainder = divmod(time_remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return "Expired" if obj.is_overdue else "No deadline"

    def get_status_badge(self, obj):
        colors = {
            'available': 'green',
            'assigned': 'blue',
            'start_working': 'light-blue',
            'in_progress': 'orange',
            'completed': 'purple',
            'cancelled': 'red',
            'on_hold': 'gray',
            'proceed_to_pay': 'teal'
        }
        return {
            'color': colors.get(obj.status, 'gray'),
            'text': obj.get_status_display()
        }

    def get_payment_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'failed': 'red',
            'refunded': 'purple'
        }
        return {
            'color': colors.get(obj.payment_status, 'gray'),
            'text': obj.get_payment_status_display()
        }

    def get_priority_badge(self, obj):
        colors = {
            'low': '#28a745',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'urgent': '#dc3545'
        }
        return {
            'color': colors.get(obj.priority, '#6c757d'),
            'text': obj.priority.upper()
        }

    def get_cost_display(self, obj):
        if obj.cost:
            return f'${obj.cost:,.2f}'
        return 'N/A'

    def get_deadline_info(self, obj):
        if not obj.deadline:
            return {'text': 'No deadline', 'color': 'gray'}
        
        now = timezone.now()
        deadline_str = obj.deadline.strftime('%m/%d/%Y %H:%M')
        
        if obj.deadline < now and obj.status not in ['completed', 'cancelled']:
            return {
                'text': f'OVERDUE - {deadline_str}',
                'color': 'red',
                'is_overdue': True
            }
        elif obj.deadline < now + timezone.timedelta(days=1):
            return {
                'text': f'DUE SOON - {deadline_str}',
                'color': 'orange',
                'is_due_soon': True
            }
        else:
            return {
                'text': deadline_str,
                'color': 'black'
            }

    def get_title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title

# Bid Serializers
class BidSerializer(serializers.ModelSerializer):
    freelancer = FreelancerSerializer(read_only=True)
    order = BaseServiceSerializer(read_only=True)
    client_info = serializers.SerializerMethodField()
    freelancer_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    status_badge = serializers.SerializerMethodField()
    created_at_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Bid
        fields = [
            'id', 'order', 'freelancer', 'bid_amount', 'estimated_hours', 
            'proposal', 'status', 'status_display', 'status_badge',
            'created_at', 'created_at_display', 'updated_at',
            'approved_by', 'approved_at',
            'client_info', 'freelancer_info'
        ]
        read_only_fields = ('created_at', 'updated_at', 'approved_at')

    def get_client_info(self, obj):
        """Get client information from the order"""
        return {
            'id': obj.order.user.id,
            'email': obj.order.user.email,
            'name': f"{obj.order.user.first_name} {obj.order.user.last_name}",
            'client_id': f"CLIENT-{obj.order.user.id:03d}"
        }

    def get_freelancer_info(self, obj):
        """Get detailed freelancer information"""
        freelancer = obj.freelancer
        return {
            'id': freelancer.id,
            'user_id': freelancer.user.id,
            'name': freelancer.display_name,
            'email': freelancer.user.email,
            'freelancer_type': freelancer.freelancer_type,
            'freelancer_type_display': freelancer.get_freelancer_type_display(),
            'hourly_rate': freelancer.hourly_rate,
            'rating': freelancer.average_rating,
            'completed_projects': freelancer.total_projects_completed
        }

    def get_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'withdrawn': 'gray',
            'under_review': 'blue',
            'revision_requested': 'yellow'
        }
        return {
            'color': colors.get(obj.status, 'gray'),
            'text': obj.get_status_display()
        }

    def get_created_at_display(self, obj):
        return obj.created_at.strftime('%b %d, %Y %I:%M %p') if obj.created_at else None

class BidCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bid
        fields = ['bid_amount', 'estimated_hours', 'proposal']

    def create(self, validated_data):
        request = self.context.get('request')
        order = self.context.get('order')
        
        try:
            freelancer = request.user.freelancer_profile
        except:
            raise serializers.ValidationError("You must have a freelancer profile to place bids")
            
        if not freelancer.is_available:
            raise serializers.ValidationError("You are not available for new orders")
            
        validated_data['freelancer'] = freelancer
        validated_data['order'] = order
        
        return super().create(validated_data)


class BidActionSerializer(serializers.Serializer):
    """Serializer for bid approval/rejection actions"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    notes = serializers.CharField(required=False, allow_blank=True)

    def update_bid_status(self, bid, validated_data):
        action = validated_data['action']
        request = self.context.get('request')
        
        if action == 'approve':
            bid.status = 'approved'
            bid.approved_by = request.user if request else None
            bid.approved_at = timezone.now()
        elif action == 'reject':
            bid.status = 'rejected'
            
        bid.save()
        return bid


# Admin List Serializer (optimized for tables)
class ServiceListSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    assigned_to_name = serializers.CharField(read_only=True)
    assigned_to_info = serializers.SerializerMethodField()
    client_id = serializers.CharField(read_only=True)
    client_info = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    time_remaining_display = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()
    
    # Display fields
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    # Badge fields
    status_badge = serializers.SerializerMethodField()
    payment_status_badge = serializers.SerializerMethodField()
    priority_badge = serializers.SerializerMethodField()
    cost_display = serializers.SerializerMethodField()
    deadline_info = serializers.SerializerMethodField()
    title_short = serializers.SerializerMethodField()

    class Meta:
        model = BaseService
        fields = '__all__' 

    def get_assigned_to_info(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.display_name} ({obj.assigned_to.get_freelancer_type_display()})"
        return 'Unassigned'

    def get_client_info(self, obj):
        return f"{obj.user.email} ({obj.client_id})"

    def get_files_count(self, obj):
        return obj.files.count()

    def get_time_remaining_display(self, obj):
        time_remaining = obj.time_remaining
        if time_remaining:
            days = time_remaining.days
            hours, remainder = divmod(time_remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return "Expired" if obj.is_overdue else "No deadline"

    def get_status_badge(self, obj):
        colors = {
            'available': 'green',
            'assigned': 'blue',
            'start_working': 'light-blue',
            'in_progress': 'orange',
            'completed': 'purple',
            'cancelled': 'red',
            'on_hold': 'gray',
            'proceed_to_pay': 'teal'
        }
        return {
            'color': colors.get(obj.status, 'gray'),
            'text': obj.get_status_display()
        }

    def get_payment_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'failed': 'red',
            'refunded': 'purple'
        }
        return {
            'color': colors.get(obj.payment_status, 'gray'),
            'text': obj.get_payment_status_display()
        }

    def get_priority_badge(self, obj):
        colors = {
            'low': '#28a745',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'urgent': '#dc3545'
        }
        return {
            'color': colors.get(obj.priority, '#6c757d'),
            'text': obj.priority.upper()
        }

    def get_cost_display(self, obj):
        if obj.cost:
            return f'${obj.cost:,.2f}'
        return 'N/A'

    def get_deadline_info(self, obj):
        if not obj.deadline:
            return 'No deadline'
        
        now = timezone.now()
        deadline_str = obj.deadline.strftime('%m/%d/%Y %H:%M')
        
        if obj.deadline < now and obj.status not in ['completed', 'cancelled']:
            return f'OVERDUE - {deadline_str}'
        elif obj.deadline < now + timezone.timedelta(days=1):
            return f'DUE SOON - {deadline_str}'
        else:
            return deadline_str

    def get_title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title


# Creation Serializers
class BaseServiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseService
        fields = [
            'title', 'description', 'service_type', 'cost', 'deadline', 
            'priority', 'requirements', 'tags', 'notes', 'estimated_hours'
        ]
        extra_kwargs = {
            'deadline': {'required': False},
            'cost': {'required': False},
            'priority': {'default': 'medium'}
        }

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['user'] = request.user
        return super().create(validated_data)


class SoftwareServiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoftwareService
        fields = [
            'title', 'description', 'cost', 'deadline', 'requirements', 'tags',
            'priority', 'estimated_hours', 'budget_range', 'timeline', 
            'frontend_languages', 'frontend_frameworks', 'backend_languages', 
            'backend_frameworks', 'ai_languages', 'ai_frameworks'
        ]
        extra_kwargs = {
            'deadline': {'required': False},
            'cost': {'required': False},
            'priority': {'default': 'medium'}
        }

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['user'] = request.user
        return super().create(validated_data)


class ResearchServiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchService
        fields = [
            'title', 'description', 'cost', 'deadline', 'requirements', 'tags',
            'priority', 'estimated_hours', 'academic_writing_type', 'writing_technique', 
            'academic_writing_style', 'critical_writing_type', 'critical_thinking_skill',
            'critical_writing_structure', 'discussion_type', 'discussion_component',
            'citation_style', 'number_of_pages', 'number_of_references', 'study_level'
        ]
        extra_kwargs = {
            'deadline': {'required': False},
            'cost': {'required': False},
            'priority': {'default': 'medium'}
        }

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['user'] = request.user
        return super().create(validated_data)


class CustomServiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomService
        fields = [
            'title', 'description', 'cost', 'deadline', 'requirements', 'tags',
            'priority', 'estimated_hours', 'sizes', 'phone_number', 
            'delivery_time', 'support_duration', 'features', 'process_link', 'service_id'
        ]
        extra_kwargs = {
            'deadline': {'required': False},
            'cost': {'required': False},
            'priority': {'default': 'medium'}
        }

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['user'] = request.user
        return super().create(validated_data)


# Admin Action Serializers
class OrderAssignmentSerializer(serializers.Serializer):
    freelancer_id = serializers.CharField(max_length=20)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_freelancer_id(self, value):
        try:
            freelancer = Freelancer.objects.get(id=value)
            if not freelancer.is_available:
                raise serializers.ValidationError("Selected freelancer is not available")
            return value
        except Freelancer.DoesNotExist:
            raise serializers.ValidationError("Freelancer not found")



class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    notes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = BaseService
        fields = ['status', 'notes']

    def update(self, instance, validated_data):
        notes = validated_data.pop('notes', '')
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        instance = super().update(instance, validated_data)
        
        if old_status != new_status:
            request = self.context.get('request')
            OrderStatusHistory.objects.create(
                order=instance,
                previous_status=old_status,
                new_status=new_status,
                changed_by=request.user if request else None,
                notes=notes
            )
        
        return instance


class ServicePaymentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseService
        fields = ['payment_status', 'status']


class OrderActionSerializer(serializers.Serializer):
    """Serializer for handling various order actions"""
    action = serializers.ChoiceField(choices=[
        'assign', 'reassign', 'make_available', 'put_on_hold', 
        'cancel', 'start_progress', 'complete', 'proceed_to_pay'
    ])
    freelancer_id = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        action = data.get('action')
        freelancer_id = data.get('freelancer_id')
        
        if action in ['assign', 'reassign'] and not freelancer_id:
            raise serializers.ValidationError({
                'freelancer_id': 'This field is required for assignment actions'
            })
            
        if freelancer_id:
            try:
                freelancer = Freelancer.objects.get(id=freelancer_id)
                if not freelancer.is_available:
                    raise serializers.ValidationError({
                        'freelancer_id': 'Selected freelancer is not available'
                    })
            except Freelancer.DoesNotExist:
                raise serializers.ValidationError({
                    'freelancer_id': 'Freelancer not found'
                })
        
        return data


# Statistics/Dashboard Serializers
class OrderStatsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    available_orders = serializers.IntegerField()
    assigned_orders = serializers.IntegerField()
    start_working_orders = serializers.IntegerField()
    in_progress_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    on_hold_orders = serializers.IntegerField()
    proceed_to_pay_orders = serializers.IntegerField()
    overdue_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_payment = serializers.DecimalField(max_digits=10, decimal_places=2)
    status_counts = serializers.DictField()
    payment_status_counts = serializers.DictField()


class FreelancerStatsSerializer(serializers.Serializer):
    total_freelancers = serializers.IntegerField()
    available_freelancers = serializers.IntegerField()
    busy_freelancers = serializers.IntegerField()
    freelancers_by_type = serializers.DictField()
    freelancers_by_experience = serializers.DictField()


# Specialized Service Serializers
class SoftwareServiceSerializer(BaseServiceSerializer):
    class Meta(BaseServiceSerializer.Meta):
        model = SoftwareService
        fields = '__all__'


class ResearchServiceSerializer(BaseServiceSerializer):
    class Meta(BaseServiceSerializer.Meta):
        model = ResearchService
        fields = '__all__'


class CustomServiceSerializer(BaseServiceSerializer):
    class Meta(BaseServiceSerializer.Meta):
        model = CustomService
        fields = '__all__'


# Export Serializer for CSV functionality
class OrderExportSerializer(serializers.ModelSerializer):
    """Serializer for CSV export matching admin export format"""
    client_email = serializers.CharField(source='user.email', read_only=True)
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    assigned_to_name = serializers.CharField(read_only=True)
    deadline_formatted = serializers.SerializerMethodField()
    created_formatted = serializers.SerializerMethodField()

    class Meta:
        model = BaseService
        fields = [
            'id', 'title', 'client_email', 'service_type_display', 'status_display',
            'payment_status_display', 'assigned_to_name', 'cost', 'deadline_formatted',
            'created_formatted', 'priority_display'
        ]

    def get_deadline_formatted(self, obj):
        return obj.deadline.strftime('%Y-%m-%d %H:%M') if obj.deadline else 'No deadline'

    def get_created_formatted(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    
class AdminDashboardSerializer(serializers.Serializer):
    stats = serializers.DictField()
    chart_data = serializers.ListField()
    recent_tasks = BaseServiceSerializer(many=True)
    top_freelancers = FreelancerSerializer(many=True)
    status_distribution = serializers.ListField()
    recent_activity = OrderStatusHistorySerializer(many=True)