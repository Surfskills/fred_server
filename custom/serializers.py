from rest_framework import serializers
from .models import SoftwareRequest, ResearchRequest

class BaseRequestSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True
        fields = ('id', 'title', 'project_description', 'request_type', 'user', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')

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
            'budget_range', 'timeline', 'frontend_languages', 
            'frontend_frameworks', 'backend_languages', 
            'backend_frameworks', 'ai_languages', 'ai_frameworks'
        )

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['request_type'] = 'software'
        return super().create(validated_data)

class ResearchRequestSerializer(BaseRequestSerializer):
    class Meta(BaseRequestSerializer.Meta):
        model = ResearchRequest
        fields = BaseRequestSerializer.Meta.fields + (
            'academic_writing_type', 'writing_technique', 
            'research_paper_structure', 'academic_writing_style',
            'research_paper_writing_process', 'critical_writing_type',
            'critical_thinking_skill', 'critical_writing_structure',
            'discussion_type', 'discussion_component',
            'academic_writing_tool', 'research_paper_database',
            'plagiarism_checker', 'reference_management_tool',
            'academic_discussion_type', 'citation_style'
        )

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['request_type'] = 'research'
        return super().create(validated_data)

class RequestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoftwareRequest  # Using SoftwareRequest as base model
        fields = ('id', 'title', 'project_description', 'request_type', 'created_at', 'updated_at')
        read_only_fields = fields

    def to_representation(self, instance):
        if isinstance(instance, SoftwareRequest):
            return SoftwareRequestSerializer(instance).data
        elif isinstance(instance, ResearchRequest):
            return ResearchRequestSerializer(instance).data
        return super().to_representation(instance) 