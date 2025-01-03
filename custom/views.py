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
        
        # Check for both camelCase and snake_case versions of request_type
        request_type = request.data.get('request_type') or request.data.get('requestType')
        
        if not request_type:
            return Response(
                {
                    'error': 'request_type is required',
                    'received_data': request.data,
                    'note': 'Please send either request_type or requestType in the request data'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert data keys from camelCase to snake_case
        data = {}
        
        # Get budget range value (handle both camelCase and snake_case)
        budget_range = request.data.get('budgetRange') or request.data.get('budget_range')
        print(f"Original budget_range value: {budget_range}")  # Debug print
        
        for key, value in request.data.items():
            # Convert camelCase to snake_case
            snake_key = ''.join(['_' + c.lower() if c.isupper() else c for c in key]).lstrip('_')
            
            # Handle budget range separately
            if snake_key == 'budget_range':
                continue  # Skip here, we'll add it later
                
            data[snake_key] = value
        
        # Add budget_range to data with proper value
        if budget_range:
            print(f"Processing budget_range: {budget_range}")  # Debug print
            data['budget_range'] = budget_range
            print(f"Final budget_range value: {data['budget_range']}")  # Debug print
        
        print("Converted data:", data)  # Debug print
        print("Available budget choices:", dict(SoftwareRequest.BUDGET_RANGES))  # Debug print
        
        if request_type.lower() == 'software':
            serializer = SoftwareRequestSerializer(
                data=data,
                context={'request': request}
            )
            print("Using SoftwareRequestSerializer")  # Debug print
        elif request_type.lower() == 'research':
            serializer = ResearchRequestSerializer(
                data=data,
                context={'request': request}
            )
            print("Using ResearchRequestSerializer")  # Debug print
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
                # Set the user before saving
                serializer.validated_data['user'] = request.user
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
                'received_data': data,
                'model_choices': dict(SoftwareRequest.BUDGET_RANGES),  # Show available choices
                'note': 'Make sure budget_range matches one of the available choices exactly'
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