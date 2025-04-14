from django.http import Http404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Value, CharField

from rest_framework.exceptions import PermissionDenied

from .models import SoftwareRequest, ResearchRequest
from .serializers import (
    SoftwareRequestSerializer,
    ResearchRequestSerializer,
)


from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from django.http import Http404
from django.db.models import Value, CharField
from .models import SoftwareRequest, ResearchRequest
from .serializers import SoftwareRequestSerializer, ResearchRequestSerializer

class RequestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_queryset(self, request_type=None):
        user = self.request.user
        
        if request_type == 'software':
            return SoftwareRequest.objects.filter(user=user)
        elif request_type == 'research':
            return ResearchRequest.objects.filter(user=user)

        # Merge software and research requests
        software_requests = SoftwareRequest.objects.filter(user=user).annotate(
            model_type=Value('software', output_field=CharField()),
            # Add NULLs for research-specific fields
            academic_writing_type=Value(None, output_field=CharField(null=True)),
            # ... (you can leave the rest as-is)
        ).values(...)

        research_requests = ResearchRequest.objects.filter(user=user).annotate(
            model_type=Value('research', output_field=CharField()),
            # Add NULLs for software-specific fields
            budget_range=Value(None, output_field=CharField(null=True)),
            # ... (you can leave the rest as-is)
        ).values(...)

        return software_requests.union(research_requests).order_by('-created_at')

    def get_object_by_shared_id(self, shared_id):
        """
        Look up a request (software or research) by shared_id and ensure it belongs to the user.
        """
        user = self.request.user
        try:
            obj = SoftwareRequest.objects.get(shared_id=shared_id, user=user)
            return obj, SoftwareRequestSerializer
        except SoftwareRequest.DoesNotExist:
            try:
                obj = ResearchRequest.objects.get(shared_id=shared_id, user=user)
                return obj, ResearchRequestSerializer
            except ResearchRequest.DoesNotExist:
                raise PermissionDenied("Request not found or you don't have permission to access it.")

    def list(self, request):
        """Get all requests for the authenticated user"""
        queryset = self.get_queryset()
        return Response(list(queryset), status=status.HTTP_200_OK)

    def create(self, request):
        """Create a new request"""
        request_type = request.data.get('request_type')
        if not request_type:
            return Response({'error': 'request_type is required'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data['user'] = request.user.id

        if request_type == 'software':
            serializer = SoftwareRequestSerializer(data=data, context={'request': request})
        elif request_type == 'research':
            serializer = ResearchRequestSerializer(data=data, context={'request': request})
        else:
            return Response({'error': f'Invalid request type: {request_type}'}, status=status.HTTP_400_BAD_REQUEST)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response({'error': 'Invalid data', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, shared_id=None):
        """Retrieve a request by shared_id"""
        instance, serializer_class = self.get_object_by_shared_id(shared_id)
        serializer = serializer_class(instance)
        return Response(serializer.data)

    def update(self, request, shared_id=None):
        """Update a request by shared_id"""
        instance, serializer_class = self.get_object_by_shared_id(shared_id)
        serializer = serializer_class(instance, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response({'error': 'Invalid data', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def can_delete_request(self, instance):
        """Disallow deleting paid orders"""
        if instance.payment_status == 'paid':
            raise PermissionDenied("Cannot delete a paid order.")
        return True

    def destroy(self, request, shared_id=None):
        """Delete a request by shared_id"""
        instance, _ = self.get_object_by_shared_id(shared_id)
        self.can_delete_request(instance)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def software(self, request):
        queryset = self.get_queryset(request_type='software')
        serializer = SoftwareRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def research(self, request):
        queryset = self.get_queryset(request_type='research')
        serializer = ResearchRequestSerializer(queryset, many=True)
        return Response(serializer.data)
