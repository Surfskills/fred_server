from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Q
from itertools import chain
from .models import SoftwareRequest, ResearchRequest
from .serializers import (
    SoftwareRequestSerializer,
    ResearchRequestSerializer,
    RequestListSerializer
)

class RequestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_queryset(self, request_type=None):
        user = self.request.user
        software_requests = SoftwareRequest.objects.filter(user=user)
        research_requests = ResearchRequest.objects.filter(user=user)

        if request_type == 'software':
            return software_requests
        elif request_type == 'research':
            return research_requests
        
        # Combine both querysets for listing all requests
        return sorted(
            chain(software_requests, research_requests),
            key=lambda instance: instance.created_at,
            reverse=True
        )

    def list(self, request):
        """Get all requests for the authenticated user"""
        queryset = self.get_queryset()
        serializer = RequestListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        """Create a new request"""
        print("Received data:", request.data)  # Debug print
        request_type = request.data.get('request_type')
        
        if not request_type:
            return Response(
                {'error': 'request_type is required', 'received_data': request.data},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if request_type == 'software':
            serializer = SoftwareRequestSerializer(
                data=request.data,
                context={'request': request}
            )
        elif request_type == 'research':
            serializer = ResearchRequestSerializer(
                data=request.data,
                context={'request': request}
            )
        else:
            return Response(
                {
                    'error': 'Invalid request type',
                    'received_type': request_type,
                    'allowed_types': ['software', 'research']
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if serializer.is_valid():
            try:
                instance = serializer.save()
                print(f"Created {request_type} request with ID: {instance.id}")  # Debug print
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(f"Error saving request: {str(e)}")  # Debug print
                return Response(
                    {
                        'error': 'Error saving request',
                        'detail': str(e)
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        print("Validation errors:", serializer.errors)  # Debug print
        return Response(
            {
                'error': 'Invalid data provided',
                'validation_errors': serializer.errors,
                'received_data': request.data
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    def retrieve(self, request, pk=None):
        """Get a specific request by ID"""
        try:
            # Try to find in software requests
            instance = SoftwareRequest.objects.get(pk=pk, user=request.user)
            serializer = SoftwareRequestSerializer(instance)
        except SoftwareRequest.DoesNotExist:
            try:
                # Try to find in research requests
                instance = ResearchRequest.objects.get(pk=pk, user=request.user)
                serializer = ResearchRequestSerializer(instance)
            except ResearchRequest.DoesNotExist:
                return Response(
                    {'error': 'Request not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.data)

    def update(self, request, pk=None):
        """Update a specific request"""
        try:
            # Try to find in software requests
            instance = SoftwareRequest.objects.get(pk=pk, user=request.user)
            serializer = SoftwareRequestSerializer(
                instance,
                data=request.data,
                context={'request': request},
                partial=True
            )
        except SoftwareRequest.DoesNotExist:
            try:
                # Try to find in research requests
                instance = ResearchRequest.objects.get(pk=pk, user=request.user)
                serializer = ResearchRequestSerializer(
                    instance,
                    data=request.data,
                    context={'request': request},
                    partial=True
                )
            except ResearchRequest.DoesNotExist:
                return Response(
                    {'error': 'Request not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(
            {
                'error': 'Invalid data provided',
                'validation_errors': serializer.errors,
                'received_data': request.data
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, pk=None):
        """Delete a specific request"""
        try:
            # Try to find and delete in software requests
            instance = SoftwareRequest.objects.get(pk=pk, user=request.user)
        except SoftwareRequest.DoesNotExist:
            try:
                # Try to find and delete in research requests
                instance = ResearchRequest.objects.get(pk=pk, user=request.user)
            except ResearchRequest.DoesNotExist:
                return Response(
                    {'error': 'Request not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def software(self, request):
        """Get all software requests"""
        queryset = self.get_queryset(request_type='software')
        serializer = SoftwareRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def research(self, request):
        """Get all research requests"""
        queryset = self.get_queryset(request_type='research')
        serializer = ResearchRequestSerializer(queryset, many=True)
        return Response(serializer.data)