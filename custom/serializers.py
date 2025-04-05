from rest_framework import serializers

from service.models import Service
from service.serializers import ServiceSerializer
from .models import SoftwareRequest, ResearchRequest, IDManager

class BaseRequestSerializer(serializers.ModelSerializer):
    # Use id as the field name instead of id_manager
    id = serializers.PrimaryKeyRelatedField(source='id_manager.id', read_only=True)
    
    class Meta:
        abstract = True
        fields = (
            'id', 
            'title', 
            'project_description',
            'cost',
            'request_type', 
            'user', 
            'status',
            'payment_status',
            'order_status',
            'created_at', 
            'updated_at',
            'acceptance_status'
        )
        read_only_fields = ('user', 'created_at', 'updated_at')

    def validate(self, attrs):
        if not self.context.get('request'):
            raise serializers.ValidationError("Request context is required")
        if not self.context['request'].user:
            raise serializers.ValidationError("User must be authenticated")
        return attrs
        
    def create(self, validated_data):
        # Create a new IDManager instance to get a new primary key
        id_manager = IDManager.objects.create()
        validated_data['id_manager'] = id_manager
        return super().create(validated_data)

class SoftwareRequestSerializer(BaseRequestSerializer):
    class Meta(BaseRequestSerializer.Meta):
        model = SoftwareRequest
        fields = BaseRequestSerializer.Meta.fields + (
            'budget_range',
            'timeline',
            'frontend_languages',
            'frontend_frameworks',
            'backend_languages',
            'backend_frameworks',
            'ai_languages',
            'ai_frameworks'
        )

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['request_type'] = 'software'
        return super().create(validated_data)

class ResearchRequestSerializer(BaseRequestSerializer):
    class Meta(BaseRequestSerializer.Meta):
        model = ResearchRequest
        fields = BaseRequestSerializer.Meta.fields + (
            'academic_writing_type',
            'writing_technique',
            'academic_writing_style',
            'critical_writing_type',
            'critical_thinking_skill',
            'critical_writing_structure',
            'discussion_type',
            'discussion_component',
            'citation_style',
            'number_of_pages',
            'number_of_references',
            'study_level'
        )

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['request_type'] = 'research'
        return super().create(validated_data)
    
class RequestListSerializer(serializers.Serializer):
    # Base fields
    id = serializers.IntegerField()
    shared_id = serializers.IntegerField(required=False)
    title = serializers.CharField()
    project_description = serializers.CharField()
    cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    request_type = serializers.CharField()
    status = serializers.CharField()
    payment_status = serializers.CharField()
    order_status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    # Software request specific fields
    budget_range = serializers.CharField(required=False)
    timeline = serializers.CharField(required=False)
    frontend_languages = serializers.CharField(required=False)
    frontend_frameworks = serializers.CharField(required=False)
    backend_languages = serializers.CharField(required=False)
    backend_frameworks = serializers.CharField(required=False)
    ai_languages = serializers.CharField(required=False)
    ai_frameworks = serializers.CharField(required=False)

    # Research request specific fields
    academic_writing_type = serializers.CharField(required=False)
    writing_technique = serializers.CharField(required=False)
    academic_writing_style = serializers.CharField(required=False)
    critical_writing_type = serializers.CharField(required=False)
    critical_thinking_skill = serializers.CharField(required=False)
    critical_writing_structure = serializers.CharField(required=False)
    discussion_type = serializers.CharField(required=False)
    discussion_component = serializers.CharField(required=False)
    citation_style = serializers.CharField(required=False)
    number_of_pages = serializers.IntegerField(required=False)
    number_of_references = serializers.IntegerField(required=False)
    study_level = serializers.CharField(required=False)

    def to_representation(self, instance):
        if hasattr(instance, 'id_manager'):
            # For models with id_manager
            if isinstance(instance, SoftwareRequest):
                serializer = SoftwareRequestSerializer(instance)
            elif isinstance(instance, ResearchRequest):
                serializer = ResearchRequestSerializer(instance)
            elif isinstance(instance, Service):
                serializer = ServiceSerializer(instance)
            else:
                return super().to_representation(instance)
                
            data = serializer.data
            # Add shared_id if it's missing
            if 'shared_id' not in data and hasattr(instance, 'id_manager') and instance.id_manager:
                data['shared_id'] = instance.id_manager.id
            return data
        else:
            # Fall back to default behavior
            return super().to_representation(instance)