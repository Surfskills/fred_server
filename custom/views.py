from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Q, Value, CharField
from django.db.models.functions import Cast
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
        
        if request_type == 'software':
            return SoftwareRequest.objects.filter(user=user)
        elif request_type == 'research':
            return ResearchRequest.objects.filter(user=user)
        
        # Annotate common fields for both querysets
        software_requests = SoftwareRequest.objects.filter(user=user).annotate(
            model_type=Value('software', output_field=CharField()),
            # Add NULL values for research-specific fields
            academic_writing_type=Value(None, output_field=CharField(null=True)),
            writing_technique=Value(None, output_field=CharField(null=True)),
            research_paper_structure=Value(None, output_field=CharField(null=True)),
            academic_writing_style=Value(None, output_field=CharField(null=True)),
            research_paper_writing_process=Value(None, output_field=CharField(null=True)),
            critical_writing_type=Value(None, output_field=CharField(null=True)),
            critical_thinking_skill=Value(None, output_field=CharField(null=True)),
            critical_writing_structure=Value(None, output_field=CharField(null=True)),
            discussion_type=Value(None, output_field=CharField(null=True)),
            discussion_component=Value(None, output_field=CharField(null=True)),
            academic_writing_tool=Value(None, output_field=CharField(null=True)),
            research_paper_database=Value(None, output_field=CharField(null=True)),
            plagiarism_checker=Value(None, output_field=CharField(null=True)),
            reference_management_tool=Value(None, output_field=CharField(null=True)),
            academic_discussion_type=Value(None, output_field=CharField(null=True)),
            citation_style=Value(None, output_field=CharField(null=True))
        ).values(
            'id', 'title', 'project_description', 'request_type',
            'created_at', 'updated_at', 'user_id', 'model_type',
            'status', 'payment_status', 'order_status',
            'budget_range', 'timeline', 'frontend_languages',
            'frontend_frameworks', 'backend_languages', 'backend_frameworks',
            'ai_languages', 'ai_frameworks',
            'academic_writing_type', 'writing_technique',
            'research_paper_structure', 'academic_writing_style',
            'research_paper_writing_process', 'critical_writing_type',
            'critical_thinking_skill', 'critical_writing_structure',
            'discussion_type', 'discussion_component',
            'academic_writing_tool', 'research_paper_database',
            'plagiarism_checker', 'reference_management_tool',
            'academic_discussion_type', 'citation_style'
        )
        
        research_requests = ResearchRequest.objects.filter(user=user).annotate(
            model_type=Value('research', output_field=CharField()),
            # Add NULL values for software-specific fields
            budget_range=Value(None, output_field=CharField(null=True)),
            timeline=Value(None, output_field=CharField(null=True)),
            frontend_languages=Value(None, output_field=CharField(null=True)),
            frontend_frameworks=Value(None, output_field=CharField(null=True)),
            backend_languages=Value(None, output_field=CharField(null=True)),
            backend_frameworks=Value(None, output_field=CharField(null=True)),
            ai_languages=Value(None, output_field=CharField(null=True)),
            ai_frameworks=Value(None, output_field=CharField(null=True))
        ).values(
            'id', 'title', 'project_description', 'request_type',
            'created_at', 'updated_at', 'user_id', 'model_type',
            'status', 'payment_status', 'order_status',
            'budget_range', 'timeline', 'frontend_languages',
            'frontend_frameworks', 'backend_languages', 'backend_frameworks',
            'ai_languages', 'ai_frameworks',
            'academic_writing_type', 'writing_technique',
            'research_paper_structure', 'academic_writing_style',
            'research_paper_writing_process', 'critical_writing_type',
            'critical_thinking_skill', 'critical_writing_structure',
            'discussion_type', 'discussion_component',
            'academic_writing_tool', 'research_paper_database',
            'plagiarism_checker', 'reference_management_tool',
            'academic_discussion_type', 'citation_style'
        )
        
        # Combine querysets using UNION
        return software_requests.union(research_requests).order_by('-created_at')

    def list(self, request):
        """Get all requests for the authenticated user"""
        queryset = self.get_queryset()
        return Response(list(queryset))  # Convert queryset to list for serialization

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