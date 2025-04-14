from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone
from service.models import Service, ServiceFile
from custom.models import IDManager, ResearchRequestFile, SoftwareRequest, ResearchRequest, SoftwareRequestFile
from .models import AcceptedOffer
from .serializers import AcceptedOfferSerializer, AcceptedOfferCreateSerializer
from service.serializers import ServiceSerializer
from custom.serializers import SoftwareRequestSerializer, ResearchRequestSerializer
from rest_framework.exceptions import NotFound

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
        # Filter out services that have an 'accepted' or 'completed' status
        services = Service.objects.exclude(acceptance_status__in=['accepted', 'completed'])
        service_data = ServiceSerializer(services, many=True).data
        
        # Add offer_type field to identify the type
        for item in service_data:
            item['offer_type'] = 'service'
        
        # Get all software requests except those with 'accepted' or 'completed' status
        software_requests = SoftwareRequest.objects.exclude(acceptance_status__in=['accepted', 'completed'])
        software_data = SoftwareRequestSerializer(software_requests, many=True).data
        for item in software_data:
            item['offer_type'] = 'software'
            
        # Get all research requests except those with 'accepted' or 'completed' status
        research_requests = ResearchRequest.objects.exclude(acceptance_status__in=['accepted', 'completed'])
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
        services = Service.objects.exclude(acceptance_status__in=['accepted', 'completed'])
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=['get'])
    def software_requests(self, request):
        """Get all available software requests"""
        software_requests = SoftwareRequest.objects.exclude(acceptance_status__in=['accepted', 'completed'])
        serializer = SoftwareRequestSerializer(software_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=['get'])
    def research_requests(self, request):
        """Get all available research requests"""
        research_requests = ResearchRequest.objects.exclude(acceptance_status__in=['accepted', 'completed'])
        serializer = ResearchRequestSerializer(research_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def retrieve(self, request, pk=None):
        """Get a specific offer by ID and type"""
        offer_type = request.query_params.get('type', None)
        
        if not offer_type:
            return Response({"detail": "Offer type is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            if offer_type == 'service':
                offer = get_object_or_404(Service.objects.exclude(acceptance_status__in=['accepted', 'completed']), pk=pk)
                serializer = ServiceSerializer(offer)
            elif offer_type == 'software':
                offer = get_object_or_404(SoftwareRequest.objects.exclude(acceptance_status__in=['accepted', 'completed']), pk=pk)
                serializer = SoftwareRequestSerializer(offer)
            elif offer_type == 'research':
                offer = get_object_or_404(ResearchRequest.objects.exclude(acceptance_status__in=['accepted', 'completed']), pk=pk)
                serializer = ResearchRequestSerializer(offer)
            else:
                return Response({"detail": "Invalid offer type."}, status=status.HTTP_400_BAD_REQUEST)
                
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except (Service.DoesNotExist, SoftwareRequest.DoesNotExist, ResearchRequest.DoesNotExist):
            return Response({"detail": "Offer not found."}, status=status.HTTP_404_NOT_FOUND)


class AcceptOfferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        shared_id = request.data.get('shared_id')  # Now using shared_id (IDManager's ID)
        if not shared_id:
            return Response({"detail": "Offer ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Try to find the offer by shared_id
        offer = None
        offer_type = None
        
        # Check Service
        service = Service.objects.filter(shared_id=shared_id).first()
        if service:
            offer = service
            offer_type = 'service'
        else:
            # Check SoftwareRequest
            software_request = SoftwareRequest.objects.filter(shared_id=shared_id).first()
            if software_request:
                offer = software_request
                offer_type = 'software'
            else:
                # Check ResearchRequest
                research_request = ResearchRequest.objects.filter(shared_id=shared_id).first()
                if research_request:
                    offer = research_request
                    offer_type = 'research'
        
        if not offer:
            return Response({"detail": "Offer not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if offer is already accepted
        if offer.acceptance_status == 'accepted':
            return Response(
                {"detail": "This offer has already been accepted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update acceptance status
        offer.acceptance_status = 'accepted'
        offer.save()

        # Create AcceptedOffer
        accepted_offer_data = {
            'user': request.user.id,
            'offer_type': offer_type,
            'acceptance_status': 'accepted',
            'payment_status': offer.payment_status,
            'order_status': offer.order_status,
            'cost': offer.cost
        }

        # Set the appropriate foreign key based on offer type
        if offer_type == 'service':
            accepted_offer_data['service'] = offer.id
        elif offer_type == 'software':
            accepted_offer_data['software_request'] = offer.id
        elif offer_type == 'research':
            accepted_offer_data['research_request'] = offer.id

        serializer = AcceptedOfferCreateSerializer(data=accepted_offer_data)
        if serializer.is_valid():
            accepted_offer = serializer.save()
            return Response({
                "detail": "Offer accepted successfully.",
                "accepted_offer": AcceptedOfferSerializer(accepted_offer).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


class ReturnOfferView(APIView):
    """
    Return an accepted offer
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            accepted_offer = AcceptedOffer.objects.get(id=pk, user=request.user)
        except AcceptedOffer.DoesNotExist:
            raise NotFound("Offer not found")

        if accepted_offer.acceptance_status not in ['accepted', 'in_progress']:
            return Response(
                {"detail": "Only accepted or in-progress offers can be returned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the AcceptedOffer status
        accepted_offer.acceptance_status = 'returned'
        accepted_offer.returned_at = timezone.now()
        accepted_offer.save()

        # Update the original offer's acceptance_status based on offer type
        original_offer = None
        if accepted_offer.offer_type == 'service' and accepted_offer.service:
            original_offer = accepted_offer.service
        elif accepted_offer.offer_type == 'software' and accepted_offer.software_request:
            original_offer = accepted_offer.software_request
        elif accepted_offer.offer_type == 'research' and accepted_offer.research_request:
            original_offer = accepted_offer.research_request

        # Update the original offer's acceptance_status if it exists
        if original_offer:
            original_offer.acceptance_status = 'returned'
            original_offer.save()

        return Response({"detail": "Offer returned successfully."}, status=status.HTTP_200_OK)
    
class CompleteOfferView(APIView):
    """
    Mark an offer as completed.
    Offers with status 'in_progress' or 'accepted' can be marked as completed.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            accepted_offer = AcceptedOffer.objects.get(id=pk, user=request.user)
        except AcceptedOffer.DoesNotExist:
            raise NotFound("Offer not found")

        # Allow offers that are either in_progress or accepted to be completed
        if accepted_offer.acceptance_status not in ['in_progress', 'accepted']:
            return Response(
                {"detail": "Only in-progress or accepted offers can be completed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        accepted_offer.acceptance_status = 'completed'
        accepted_offer.completed_at = timezone.now()
        accepted_offer.save()

        # Update the original offer's acceptance_status based on offer type
        original_offer = None
        if accepted_offer.offer_type == 'service' and accepted_offer.service:
            original_offer = accepted_offer.service
        elif accepted_offer.offer_type == 'software' and accepted_offer.software_request:
            original_offer = accepted_offer.software_request
        elif accepted_offer.offer_type == 'research' and accepted_offer.research_request:
            original_offer = accepted_offer.research_request

        if original_offer:
            original_offer.acceptance_status = 'completed'
            original_offer.save()

        return Response({"detail": "Offer marked as completed."}, status=status.HTTP_200_OK)

    
class StartWorkOnOfferView(APIView):
    """
    Start work on an accepted offer
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            accepted_offer = AcceptedOffer.objects.get(
                id=pk, 
                user=request.user, 
                acceptance_status='accepted'
            )
        except AcceptedOffer.DoesNotExist:
            raise NotFound("Offer not found or already started")

        accepted_offer.acceptance_status = 'in_progress'
        accepted_offer.started_at = timezone.now()
        accepted_offer.save()

        return Response({"detail": "Started work on the offer."}, status=status.HTTP_200_OK)
    
class MultiFileUploadAPIView(APIView):
    """
    API view to upload multiple files and associate them with either a Service,
    SoftwareRequest, or ResearchRequest.
    Expects multipart/form-data with:
        - upload_type: "service", "software_request", or "research_request"
        - object_id: The primary key of the object to attach files to
        - files: one or more files
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        # Get the required parameters from the request
        upload_type = request.data.get('upload_type')
        object_id = request.data.get('object_id')
        if not upload_type or not object_id:
            return Response(
                {"error": "upload_type and object_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract the files from the request
        files = request.FILES.getlist('files')
        if not files:
            return Response(
                {"error": "No files provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_files = []

        # Handle file uploads for Service orders
        if upload_type == "service":
            try:
                service = Service.objects.get(pk=object_id)
            except Service.DoesNotExist:
                return Response(
                    {"error": "Service not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            for f in files:
                sf = ServiceFile.objects.create(service=service, file=f)
                created_files.append({
                    "id": sf.id,
                    "file_url": sf.file.url,
                    "uploaded_at": sf.uploaded_at
                })

        # Handle file uploads for SoftwareRequest orders
        elif upload_type == "software_request":
            try:
                software_request = SoftwareRequest.objects.get(pk=object_id)
            except SoftwareRequest.DoesNotExist:
                return Response(
                    {"error": "Software Request not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            for f in files:
                srf = SoftwareRequestFile.objects.create(software_request=software_request, file=f)
                created_files.append({
                    "id": srf.id,
                    "file_url": srf.file.url,
                    "uploaded_at": srf.uploaded_at
                })

        # Handle file uploads for ResearchRequest orders
        elif upload_type == "research_request":
            try:
                research_request = ResearchRequest.objects.get(pk=object_id)
            except ResearchRequest.DoesNotExist:
                return Response(
                    {"error": "Research Request not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            for f in files:
                rrf = ResearchRequestFile.objects.create(research_request=research_request, file=f)
                created_files.append({
                    "id": rrf.id,
                    "file_url": rrf.file.url,
                    "uploaded_at": rrf.uploaded_at
                })
        else:
            return Response(
                {"error": "Invalid upload_type. Must be 'service', 'software_request', or 'research_request'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(created_files, status=status.HTTP_201_CREATED)