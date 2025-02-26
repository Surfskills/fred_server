from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone
import uuid

from service.models import Service
from custom.models import SoftwareRequest, ResearchRequest
from .models import AcceptedOffer
from service.serializers import ServiceSerializer
from custom.serializers import SoftwareRequestSerializer, ResearchRequestSerializer


# Public endpoints for viewing available offers
class AvailableOffersViewSet(viewsets.ViewSet):
    """
    ViewSet for retrieving available offers (services and requests)
    No authentication required - available to all users
    """
    permission_classes = [AllowAny]
    http_method_names = ['get']
    
    def list(self, request):
        """Get all available offers (both services and requests)"""
        services = Service.objects.all()
        service_data = ServiceSerializer(services, many=True).data
        
        # Add offer_type field to identify the type
        for item in service_data:
            item['offer_type'] = 'service'
        
        # Get all software and research requests
        software_requests = SoftwareRequest.objects.all()
        software_data = SoftwareRequestSerializer(software_requests, many=True).data
        for item in software_data:
            item['offer_type'] = 'software'
            
        research_requests = ResearchRequest.objects.all()
        research_data = ResearchRequestSerializer(research_requests, many=True).data
        for item in research_data:
            item['offer_type'] = 'research'
        
        # Combine all offers and sort by created_at if available
        all_offers = service_data + software_data + research_data
        all_offers.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return Response(all_offers, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=['get'])
    def services(self, request):
        """Get all available services"""
        services = Service.objects.all()
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=['get'])
    def software_requests(self, request):
        """Get all available software requests"""
        software_requests = SoftwareRequest.objects.all()
        serializer = SoftwareRequestSerializer(software_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=['get'])
    def research_requests(self, request):
        """Get all available research requests"""
        research_requests = ResearchRequest.objects.all()
        serializer = ResearchRequestSerializer(research_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def retrieve(self, request, pk=None):
        """Get a specific offer by ID and type"""
        offer_type = request.query_params.get('type', None)
        
        if not offer_type:
            return Response({"detail": "Offer type is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            if offer_type == 'service':
                offer = get_object_or_404(Service, pk=pk)
                serializer = ServiceSerializer(offer)
            elif offer_type == 'software':
                offer = get_object_or_404(SoftwareRequest, pk=pk)
                serializer = SoftwareRequestSerializer(offer)
            elif offer_type == 'research':
                offer = get_object_or_404(ResearchRequest, pk=pk)
                serializer = ResearchRequestSerializer(offer)
            else:
                return Response({"detail": "Invalid offer type."}, status=status.HTTP_400_BAD_REQUEST)
                
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except (Service.DoesNotExist, SoftwareRequest.DoesNotExist, ResearchRequest.DoesNotExist):
            return Response({"detail": "Offer not found."}, status=status.HTTP_404_NOT_FOUND)


from .serializers import AcceptedOfferSerializer

class AcceptOfferView(APIView):
    """
    API endpoint for accepting an offer
    Authentication required
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Retrieve the offer_id from the request body
        offer_id = request.data.get('offer_id')  # Ensure to pass 'offer_id' in the request body

        if not offer_id:
            return Response({"detail": "Offer ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the offer exists regardless of the offer type
        offer = None
        offer_type = None  # Track the offer type

        # Try to find the offer from one of the three models (Service, SoftwareRequest, or ResearchRequest)
        for model in [Service, SoftwareRequest, ResearchRequest]:
            try:
                offer = model.objects.get(id=offer_id)
                offer_type = model.__name__.lower()  # Get the model name dynamically (service, softwarerequest, or researchrequest)
                break  # Stop once we find the offer
            except model.DoesNotExist:
                continue  # If not found in the current model, try the next one

        if not offer:
            return Response({"detail": "Offer not found."}, status=status.HTTP_404_NOT_FOUND)

        # Generate a unique ID for the accepted offer
        unique_id = str(uuid.uuid4())
        
        # Check if the user has already accepted this offer
        existing_acceptance = None
        if offer_type == 'service':
            existing_acceptance = AcceptedOffer.objects.filter(user=request.user, service=offer).first()
        elif offer_type == 'softwarerequest':
            existing_acceptance = AcceptedOffer.objects.filter(user=request.user, software_request=offer).first()
        elif offer_type == 'researchrequest':
            existing_acceptance = AcceptedOffer.objects.filter(user=request.user, research_request=offer).first()
            
        if existing_acceptance:
            return Response({
                "detail": "You have already accepted this offer.",
                "accepted_offer_id": existing_acceptance.id
            }, status=status.HTTP_200_OK)

        # Now create the AcceptedOffer object based on the offer type
        accepted_offer = None
        if offer_type == 'service':
            accepted_offer = AcceptedOffer.objects.create(
                user=request.user,
                service=offer,  # Use the 'service' ForeignKey
                status='accepted',
                accepted_at=timezone.now(),
                offer_type='service'
            )
        elif offer_type == 'softwarerequest':
            accepted_offer = AcceptedOffer.objects.create(
                user=request.user,
                software_request=offer,  # Use the 'software_request' ForeignKey
                status='accepted',
                accepted_at=timezone.now(),
                offer_type='software'
            )
        elif offer_type == 'researchrequest':
            accepted_offer = AcceptedOffer.objects.create(
                user=request.user,
                research_request=offer,  # Use the 'research_request' ForeignKey
                status='accepted',
                accepted_at=timezone.now(),
                offer_type='research'
            )

        # Return success response with the accepted offer ID
        return Response({
            "detail": "Offer accepted successfully.",
            "accepted_offer_id": accepted_offer.id
        }, status=status.HTTP_201_CREATED)


class AcceptedOffersViewSet(viewsets.ViewSet):
    """
    ViewSet for managing accepted offers
    Authentication required
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get all offers accepted by the current user"""
        accepted_offers = AcceptedOffer.objects.filter(user=request.user)
        serializer = AcceptedOfferSerializer(accepted_offers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        """Get a specific accepted offer by ID"""
        accepted_offer = get_object_or_404(AcceptedOffer, id=pk, user=request.user)
        serializer = AcceptedOfferSerializer(accepted_offer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def start_work(self, request, pk=None):
        """Start work on an accepted offer"""
        accepted_offer = get_object_or_404(AcceptedOffer, id=pk, user=request.user, status='accepted')

        accepted_offer.status = 'in_progress'
        accepted_offer.save()

        return Response({"detail": "Started work on the offer."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark an offer as completed"""
        accepted_offer = get_object_or_404(AcceptedOffer, id=pk, user=request.user)

        if accepted_offer.status != 'in_progress':
            return Response({"detail": "Only in-progress offers can be completed."},
                             status=status.HTTP_400_BAD_REQUEST)

        accepted_offer.status = 'completed'
        accepted_offer.completed_at = timezone.now()
        accepted_offer.save()

        return Response({"detail": "Offer marked as completed."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def return_offer(self, request, pk=None):
        """Return an offer"""
        accepted_offer = get_object_or_404(AcceptedOffer, id=pk, user=request.user)

        if accepted_offer.status not in ['accepted', 'in_progress']:
            return Response({"detail": "Only accepted or in-progress offers can be returned."},
                             status=status.HTTP_400_BAD_REQUEST)

        accepted_offer.status = 'returned'
        accepted_offer.returned_at = timezone.now()
        accepted_offer.save()

        return Response({"detail": "Offer returned successfully."}, status=status.HTTP_200_OK)