from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Q
from itertools import chain
import logging
from .models import SoftwareRequest, ResearchRequest
from .serializers import SoftwareRequestSerializer, ResearchRequestSerializer, RequestListSerializer

# Set up logging
logger = logging.getLogger(__name__)

class RequestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_queryset(self, request_type=None):
        """Retrieve the queryset of requests, filtered by type if provided."""
        user = self.request.user
        software_requests = SoftwareRequest.objects.filter(user=user)
        research_requests = ResearchRequest.objects.filter(user=user)

        if request_type == 'software':
            return software_requests
        elif request_type == 'research':
            return research_requests

        # Combine both querysets for listing all requests, ordered by created_at
        combined = software_requests.union(research_requests).order_by('-created_at')
        return combined

    def list(self, request):
        """Get all requests for the authenticated user."""
        queryset = self.get_queryset()
        serializer = RequestListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        """Create a new request (software or research)."""
        request_type = request.data.get('request_type')

        if not request_type:
            return Response(
                {'error': 'request_type is required', 'received_data': request.data},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if request_type not in ['software', 'research']:
            return Response(
                {'error': 'Invalid request type', 'allowed_types': ['software', 'research']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if request_type == 'software':
            serializer = SoftwareRequestSerializer(data=request.data, context={'request': request})
        elif request_type == 'research':
            serializer = ResearchRequestSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            try:
                instance = serializer.save()
                logger.info(f"Created {request_type} request with ID: {instance.id}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Error saving request: {str(e)}")
                return Response(
                    {'error': 'Error saving request', 'detail': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        logger.error(f"Validation errors: {serializer.errors}")
        return Response(
            {'error': 'Invalid data provided', 'validation_errors': serializer.errors, 'received_data': request.data},
            status=status.HTTP_400_BAD_REQUEST
        )

    def retrieve(self, request, pk=None):
        """Get a specific request by ID."""
        instance = self.get_request_instance(pk, request.user)
        if not instance:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)

        # Serialize and return data
        if isinstance(instance, SoftwareRequest):
            serializer = SoftwareRequestSerializer(instance)
        else:
            serializer = ResearchRequestSerializer(instance)
        
        return Response(serializer.data)

    def update(self, request, pk=None):
        """Update a specific request."""
        instance = self.get_request_instance(pk, request.user)
        if not instance:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)

        # Determine which serializer to use based on instance type
        if isinstance(instance, SoftwareRequest):
            serializer = SoftwareRequestSerializer(instance, data=request.data, context={'request': request}, partial=True)
        else:
            serializer = ResearchRequestSerializer(instance, data=request.data, context={'request': request}, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        logger.error(f"Validation errors: {serializer.errors}")
        return Response(
            {'error': 'Invalid data provided', 'validation_errors': serializer.errors, 'received_data': request.data},
            status=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, pk=None):
        """Delete a specific request."""
        instance = self.get_request_instance(pk, request.user)
        if not instance:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def software(self, request):
        """Get all software requests."""
        queryset = self.get_queryset(request_type='software')
        serializer = SoftwareRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    def research(self, request):
        """Get all research requests."""
        queryset = self.get_queryset(request_type='research')
        serializer = ResearchRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    def get_request_instance(self, pk, user):
        """Helper function to get a request instance by primary key."""
        try:
            return SoftwareRequest.objects.get(pk=pk, user=user)
        except SoftwareRequest.DoesNotExist:
            try:
                return ResearchRequest.objects.get(pk=pk, user=user)
            except ResearchRequest.DoesNotExist:
                return None
