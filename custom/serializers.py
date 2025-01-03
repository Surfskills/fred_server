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
    title = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_request_type(self, obj):
        if isinstance(obj, SoftwareRequest):
            return 'software'
        elif isinstance(obj, ResearchRequest):
            return 'research'
        return None
