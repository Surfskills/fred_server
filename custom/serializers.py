from rest_framework import serializers
from .models import SoftwareRequest, ResearchRequest

class BaseRequestSerializer(serializers.ModelSerializer):
    shared_id = serializers.IntegerField(read_only=True)
    
    class Meta:
        abstract = True
        fields = (
            'id',
            'shared_id',
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
        read_only_fields = ('user', 'created_at', 'updated_at', 'shared_id')

    def validate(self, attrs):
        if not self.context.get('request'):
            raise serializers.ValidationError("Request context is required")
        if not self.context['request'].user:
            raise serializers.ValidationError("User must be authenticated")
        return attrs

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
    shared_id = serializers.IntegerField()
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
    budget_range = serializers.CharField(required=False, allow_null=True)
    timeline = serializers.CharField(required=False, allow_null=True)
    frontend_languages = serializers.CharField(required=False, allow_null=True)
    frontend_frameworks = serializers.CharField(required=False, allow_null=True)
    backend_languages = serializers.CharField(required=False, allow_null=True)
    backend_frameworks = serializers.CharField(required=False, allow_null=True)
    ai_languages = serializers.CharField(required=False, allow_null=True)
    ai_frameworks = serializers.CharField(required=False, allow_null=True)

    # Research request specific fields
    academic_writing_type = serializers.CharField(required=False, allow_null=True)
    writing_technique = serializers.CharField(required=False, allow_null=True)
    academic_writing_style = serializers.CharField(required=False, allow_null=True)
    critical_writing_type = serializers.CharField(required=False, allow_null=True)
    critical_thinking_skill = serializers.CharField(required=False, allow_null=True)
    critical_writing_structure = serializers.CharField(required=False, allow_null=True)
    discussion_type = serializers.CharField(required=False, allow_null=True)
    discussion_component = serializers.CharField(required=False, allow_null=True)
    citation_style = serializers.CharField(required=False, allow_null=True)
    number_of_pages = serializers.IntegerField(required=False, allow_null=True)
    number_of_references = serializers.IntegerField(required=False, allow_null=True)
    study_level = serializers.CharField(required=False, allow_null=True)

    def to_representation(self, instance):
        # Handle both model instances and dictionary/values queryset results
        if isinstance(instance, dict):
            # For values() queryset results
            data = instance
        else:
            # For model instances
            if isinstance(instance, SoftwareRequest):
                serializer = SoftwareRequestSerializer(instance)
            elif isinstance(instance, ResearchRequest):
                serializer = ResearchRequestSerializer(instance)

          
            else:
                return super().to_representation(instance)
            data = serializer.data
        
        # Ensure shared_id is included
        if 'shared_id' not in data and hasattr(instance, 'shared_id'):
            data['shared_id'] = instance.shared_id
            
        return data