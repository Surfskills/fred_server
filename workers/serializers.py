from rest_framework import serializers
from .models import AcceptedOffer
from service.serializers import ServiceSerializer
from custom.serializers import SoftwareRequestSerializer, ResearchRequestSerializer





class AcceptedOfferSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    software_request = SoftwareRequestSerializer(read_only=True)
    research_request = ResearchRequestSerializer(read_only=True)
    
    class Meta:
        model = AcceptedOffer
        fields = [
            'id',
            'service',
            'software_request',
            'research_request',
            'status',
            'offer_type',
            'accepted_at',
            'started_at',
            'completed_at',
            'returned_at',
        ]
        read_only_fields = ['accepted_at']


class AcceptedOfferCreateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = AcceptedOffer
        fields = [
            'service',
            'software_request',
            'research_request',
            'status',
            'offer_type',

        ]
    
    def validate(self, data):
        """
        Validate that only one related offer is provided based on offer_type
        """
        offer_type = data.get('offer_type')
        service = data.get('service')
        software_request = data.get('software_request')
        research_request = data.get('research_request')
        
        if offer_type == 'service' and not service:
            raise serializers.ValidationError("Service must be provided for service offer type")
        elif offer_type == 'software' and not software_request:
            raise serializers.ValidationError("Software request must be provided for software offer type")
        elif offer_type == 'research' and not research_request:
            raise serializers.ValidationError("Research request must be provided for research offer type")
        
        # Ensure only the relevant offer is set
        if offer_type == 'service':
            data['software_request'] = None
            data['research_request'] = None
        elif offer_type == 'software':
            data['service'] = None
            data['research_request'] = None
        elif offer_type == 'research':
            data['service'] = None
            data['software_request'] = None
            
        return data


# class AcceptedOfferUpdateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = AcceptedOffer
#         fields = ['status', 'original_data']
    
#     def validate_status(self, value):
#         """
#         Update timestamps based on status changes
#         """
#         instance = getattr(self, 'instance', None)
#         if instance and instance.status != value:
#             if value == 'in_progress' and not instance.started_at:
#                 self.context['started_at'] = True
#             elif value == 'completed' and not instance.completed_at:
#                 self.context['completed_at'] = True
#             elif value == 'returned' and not instance.returned_at:
#                 self.context['returned_at'] = True
#         return value
    
#     def update(self, instance, validated_data):
#         # Update timestamps based on status changes
#         from django.utils import timezone
        
#         if self.context.get('started_at'):
#             instance.started_at = timezone.now()
#         if self.context.get('completed_at'):
#             instance.completed_at = timezone.now()
#         if self.context.get('returned_at'):
#             instance.returned_at = timezone.now()
            
#         return super().update(instance, validated_data)