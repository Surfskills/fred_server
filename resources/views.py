from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from .models import Resource, ResourceCategory, ResourceTag
from .serializers import (
    ResourceSerializer, ResourceCategorySerializer, 
    ResourceTagSerializer, ResourceUploadSerializer
)
from django.http import FileResponse
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from rest_framework.permissions import IsAuthenticated
from .models import Resource, ResourceVersion

class ResourceCategoryViewSet(viewsets.ModelViewSet):
    queryset = ResourceCategory.objects.all()
    serializer_class = ResourceCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

class ResourceTagViewSet(viewsets.ModelViewSet):
    queryset = ResourceTag.objects.all()
    serializer_class = ResourceTagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            # Require authentication for creation
            permission_classes = [permissions.IsAuthenticated]
        else:
            # Allow read access for unauthenticated users
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = Resource.objects.all()
        
        # Filter based on visibility and user permissions
        user = self.request.user
        if not user.is_authenticated:
            queryset = queryset.filter(visibility='public')
        elif not user.is_staff:
            queryset = queryset.filter(
                Q(visibility='public') | 
                Q(visibility='partner', partners=user) |
                Q(uploaded_by=user)
            ).distinct()
        
        # Apply filters
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        resource_type = self.request.query_params.get('type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        visibility = self.request.query_params.get('visibility')
        if visibility and user.is_staff:
            queryset = queryset.filter(visibility=visibility)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()
        
        uploaded_by = self.request.query_params.get('uploaded_by')
        if uploaded_by:
            queryset = queryset.filter(uploaded_by__email=uploaded_by)
        
        return queryset.select_related('category', 'uploaded_by').prefetch_related('tags', 'partners', 'versions')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ResourceUploadSerializer
        return ResourceSerializer
    
    def perform_create(self, serializer):
        """
        Called when creating a new resource
        """
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        resource = self.get_object()
        resource.download_count += 1
        resource.save()
        
        file_handle = resource.file.open()
        response = FileResponse(file_handle, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{resource.file.name}"'
        return response
    
    @action(detail=True, methods=['post'])
    def increment_view(self, request, pk=None):
        resource = self.get_object()
        resource.view_count += 1
        resource.save()
        return Response({'status': 'view count incremented'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resource_metrics(request):
    """
    Get comprehensive resource metrics for dashboard
    """
    user = request.user
    
    # Base queryset with user permissions
    if user.is_staff:
        resources_qs = Resource.objects.all()
    else:
        resources_qs = Resource.objects.filter(
            Q(visibility='public') | 
            Q(visibility='partner', partners=user) |
            Q(uploaded_by=user)
        ).distinct()
    
    uploaded_by = request.query_params.get('uploaded_by')
    if uploaded_by:
        resources_qs = resources_qs.filter(uploaded_by__email=uploaded_by)
    
    # Basic counts
    total_resources = resources_qs.count()
    
    # Type distribution
    type_distribution = dict(
        resources_qs.values('resource_type')
        .annotate(count=Count('id'))
        .values_list('resource_type', 'count')
    )
    
    # Visibility distribution
    visibility_distribution = dict(
        resources_qs.values('visibility')
        .annotate(count=Count('id'))
        .values_list('visibility', 'count')
    )
    
    # Category distribution
    category_distribution = dict(
        resources_qs.values('category__name')
        .annotate(count=Count('id'))
        .values_list('category__name', 'count')
    )
    
    # Tags distribution
    tags_data = resources_qs.prefetch_related('tags').values_list('tags__name', flat=True)
    tags_distribution = {}
    for tag in tags_data:
        if tag:
            tags_distribution[tag] = tags_distribution.get(tag, 0) + 1
    
    # Partners distribution
    partners_data = resources_qs.filter(visibility='partner').prefetch_related('partners')
    partners_distribution = {}
    for resource in partners_data:
        for partner in resource.partners.all():
            partner_key = partner.email or partner.username or str(partner.id)
            partners_distribution[partner_key] = partners_distribution.get(partner_key, 0) + 1
    
    # Upload date distribution
    upload_date_data = (
        resources_qs.annotate(month=TruncMonth('upload_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    upload_date_distribution = {
        item['month'].strftime('%Y-%m') if item['month'] else 'Unknown': item['count']
        for item in upload_date_data
    }
    
    # Storage calculations
    storage_data = resources_qs.aggregate(
        total_storage=Sum('file_size'),
        total_downloads=Sum('download_count'),
        total_views=Sum('view_count')
    )
    
    total_storage_bytes = storage_data['total_storage'] or 0
    total_downloads = storage_data['total_downloads'] or 0
    total_views = storage_data['total_views'] or 0
    
    # Storage by type
    storage_by_type = dict(
        resources_qs.values('resource_type')
        .annotate(total_size=Sum('file_size'))
        .values_list('resource_type', 'total_size')
    )
    storage_by_type = {k: v or 0 for k, v in storage_by_type.items()}
    
    # Versions data
    versions_data = []
    if uploaded_by:
        user_resources = resources_qs.filter(uploaded_by__email=uploaded_by)
        versions_qs = ResourceVersion.objects.filter(
            resource__in=user_resources
        ).select_related('created_by', 'resource').order_by('-created_at')[:10]
        
        for version in versions_qs:
            versions_data.append({
                'id': str(version.id),
                'version': version.version,
                'notes': version.notes,
                'file': version.file.name if version.file else '',
                'created_at': version.created_at.isoformat(),
                'created_by': version.created_by.email if version.created_by else '',
            })
    
    response_data = {
        'resources': {
            'total_resources': total_resources,
            'type_distribution': type_distribution,
            'visibility_distribution': visibility_distribution,
            'category_distribution': category_distribution,
            'tags_distribution': tags_distribution,
            'partners_distribution': partners_distribution,
            'upload_date_distribution': upload_date_distribution,
            'total_storage_bytes': total_storage_bytes,
            'storage_by_type': storage_by_type,
            'download_count': total_downloads,
            'view_count': total_views,
            'uploaded_by': uploaded_by or '',
            'versions': versions_data,
        },
        'documents': {
            'total_documents': total_resources,
            'verified_count': 0,
        }
    }
    
    return Response(response_data)