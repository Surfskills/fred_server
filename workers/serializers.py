from rest_framework import serializers

from custom.serializers import ResearchRequestSerializer, SoftwareRequestSerializer
from service.serializers import ServiceSerializer
from .models import AcceptedOffer

class AcceptedOfferSerializer(serializers.ModelSerializer):
    service_details = serializers.SerializerMethodField()
    software_request_details = serializers.SerializerMethodField()
    research_request_details = serializers.SerializerMethodField()
    
    # Add these computed fields to access common attributes across offer types
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    cost = serializers.SerializerMethodField()

    class Meta:
        model = AcceptedOffer
        fields = [
            'id', 'user', 'service', 'software_request', 'research_request', 
            'offer_type', 'status', 'accepted_at', 'completed_at', 'returned_at',
            'service_details', 'software_request_details', 'research_request_details',
            'title', 'description', 'cost' 
        ]

    # Existing methods for detailed information
    def get_service_details(self, obj):
        if obj.service:
            return ServiceSerializer(obj.service).data
        return None

    def get_software_request_details(self, obj):
        if obj.software_request:
            return SoftwareRequestSerializer(obj.software_request).data
        return None

    def get_research_request_details(self, obj):
        if obj.research_request:
            return ResearchRequestSerializer(obj.research_request).data
        return None
    
    # New methods to access common attributes
    def get_title(self, obj):
        if obj.service:
            return obj.service.title
        elif obj.software_request:
            return obj.software_request.title
        elif obj.research_request:
            return obj.research_request.title
        return None
        
    def get_description(self, obj):
        if obj.service:
            return obj.service.description
        elif obj.software_request:
            return obj.software_request.project_description
        elif obj.research_request:
            return obj.research_request.project_description
        return None
        
    def get_cost(self, obj):
        if obj.service:
            return obj.service.cost
        elif obj.software_request:
            return obj.software_request.cost
        elif obj.research_request:
            return obj.research_request.cost
        return None