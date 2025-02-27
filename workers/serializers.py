from rest_framework import serializers

from custom.serializers import ResearchRequestSerializer, SoftwareRequestSerializer
from service.serializers import ServiceSerializer
from .models import AcceptedOffer

class AcceptedOfferSerializer(serializers.ModelSerializer):
    # Use SerializerMethodField for all details
    offer_details = serializers.SerializerMethodField()
    
    # Common attributes across offer types
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    cost = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = AcceptedOffer
        fields = [
            'id', 'user', 'service', 'software_request', 'research_request', 
            'offer_type', 'status', 'accepted_at', 'completed_at', 'returned_at',
            'offer_details', 'title', 'description', 'cost', 'created_by', 'created_at'
        ]
        read_only_fields = ['offer_details', 'title', 'description', 'cost', 'created_by', 'created_at']

    def get_offer_details(self, obj):
        """Get complete details of the offer based on its type"""
        if obj.service:
            return ServiceSerializer(obj.service).data
        elif obj.software_request:
            return SoftwareRequestSerializer(obj.software_request).data
        elif obj.research_request:
            return ResearchRequestSerializer(obj.research_request).data
        return None
    
    def get_title(self, obj):
        """Get title from any offer type"""
        if obj.service:
            return obj.service.title
        elif obj.software_request:
            return obj.software_request.title
        elif obj.research_request:
            return obj.research_request.title
        return None
        
    def get_description(self, obj):
        """Get description from any offer type"""
        if obj.service:
            return obj.service.description
        elif obj.software_request:
            return obj.software_request.project_description
        elif obj.research_request:
            return obj.research_request.project_description
        return None
        
    def get_cost(self, obj):
        """Get cost from any offer type"""
        if obj.service:
            return obj.service.cost
        elif obj.software_request:
            return obj.software_request.cost
        elif obj.research_request:
            return obj.research_request.cost
        return None
    
    def get_created_by(self, obj):
        """Get creator from any offer type"""
        if obj.service:
            return obj.service.created_by.username if obj.service.created_by else None
        elif obj.software_request:
            return obj.software_request.created_by.username if obj.software_request.created_by else None
        elif obj.research_request:
            return obj.research_request.created_by.username if obj.research_request.created_by else None
        return None
    
    def get_created_at(self, obj):
        """Get creation date from any offer type"""
        if obj.service:
            return obj.service.created_at
        elif obj.software_request:
            return obj.software_request.created_at
        elif obj.research_request:
            return obj.research_request.created_at
        return None