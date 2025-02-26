from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone

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
        # Retrieve the offer_id and offer_type from the request body
        offer_id = request.data.get('offer_id')
        offer_type = request.data.get('offer_type')  # 'service', 'software', or 'research'

        if not offer_id or not offer_type:
            return Response(
                {"detail": "Offer ID and type are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify the offer exists based on the offer type
        try:
            if offer_type == 'service':
                offer = Service.objects.get(id=offer_id)
                # Create a new AcceptedOffer with only the service field set
                # Leave other offer fields as None
                accepted_offer = AcceptedOffer(
                    user=request.user,
                    service=offer,
                    software_request=None,
                    research_request=None,
                    offer_type=offer_type,
                    status='accepted',
                    accepted_at=timezone.now()
                )
            elif offer_type == 'software':
                offer = SoftwareRequest.objects.get(id=offer_id)
                accepted_offer = AcceptedOffer(
                    user=request.user,
                    service=None,
                    software_request=offer,
                    research_request=None,
                    offer_type=offer_type,
                    status='accepted',
                    accepted_at=timezone.now()
                )
            elif offer_type == 'research':
                offer = ResearchRequest.objects.get(id=offer_id)
                accepted_offer = AcceptedOffer(
                    user=request.user,
                    service=None,
                    software_request=None,
                    research_request=offer,
                    offer_type=offer_type,
                    status='accepted',
                    accepted_at=timezone.now()
                )
            else:
                return Response(
                    {"detail": "Invalid offer type."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (Service.DoesNotExist, SoftwareRequest.DoesNotExist, ResearchRequest.DoesNotExist):
            return Response(
                {"detail": "Offer not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if this offer has already been accepted
        existing_filters = {'user': request.user}
        
        if offer_type == 'service':
            existing_filters['service'] = offer
        elif offer_type == 'software':
            existing_filters['software_request'] = offer
        elif offer_type == 'research':
            existing_filters['research_request'] = offer
            
        existing_acceptance = AcceptedOffer.objects.filter(**existing_filters).first()

        if existing_acceptance:
            return Response(
                {
                    "detail": "You have already accepted this offer.",
                    "accepted_offer_id": existing_acceptance.id
                },
                status=status.HTTP_200_OK
            )

        # Check if another user has already accepted this offer
        if offer_type == 'service':
            existing_acceptance = AcceptedOffer.objects.filter(service=offer).exclude(user=request.user).first()
        elif offer_type == 'software':
            existing_acceptance = AcceptedOffer.objects.filter(software_request=offer).exclude(user=request.user).first()
        elif offer_type == 'research':
            existing_acceptance = AcceptedOffer.objects.filter(research_request=offer).exclude(user=request.user).first()
            
        if existing_acceptance:
            return Response(
                {"detail": "This offer has already been accepted by another user."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save the new AcceptedOffer
        try:
            accepted_offer.save()
            return Response(
                {
                    "detail": "Offer accepted successfully.",
                    "accepted_offer_id": accepted_offer.id
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": f"Error accepting offer: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
class AcceptedOffersViewSet(viewsets.ViewSet):
    """
    ViewSet for managing accepted offers.
    Authentication required.
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