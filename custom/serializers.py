from rest_framework import serializers
from .models import SoftwareRequest, ResearchRequest

class SoftwareRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoftwareRequest
        fields = '__all__'
        read_only_fields = ('user', 'status', 'created_at', 'updated_at')

class ResearchRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchRequest
        fields = '__all__'
        read_only_fields = ('user', 'status', 'created_at', 'updated_at')

class RequestListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    request_type = serializers.SerializerMethodField()
    project_title = serializers.CharField(source='title')
    project_description = serializers.CharField(source='description')
    status = serializers.CharField()
    payment_status = serializers.CharField()
    order_status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    
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
    research_paper_structure = serializers.CharField(required=False)
    academic_writing_style = serializers.CharField(required=False)

    def get_request_type(self, obj):
        if isinstance(obj, SoftwareRequest):
            return 'software'
        elif isinstance(obj, ResearchRequest):
            return 'research'
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Remove None values for fields that don't exist on the specific request type
        return {k: v for k, v in data.items() if v is not None}
