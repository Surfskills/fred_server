from rest_framework import serializers
from .models import AcceptedOffer
from service.models import Service
from custom.models import SoftwareRequest, ResearchRequest
from service.serializers import ServiceSerializer
from custom.serializers import SoftwareRequestSerializer, ResearchRequestSerializer

class AcceptedOfferSerializer(serializers.ModelSerializer):
    details = serializers.SerializerMethodField()

    class Meta:
        model = AcceptedOffer
        fields = '__all__' 
    
    def get_details(self, obj):
        """Return detailed information based on the offer type."""
        if obj.offer_type == 'service' and obj.service:
            return ServiceSerializer(obj.service).data
        elif obj.offer_type == 'software' and obj.software_request:
            return SoftwareRequestSerializer(obj.software_request).data
        elif obj.offer_type == 'research' and obj.research_request:
            return ResearchRequestSerializer(obj.research_request).data
        return None
