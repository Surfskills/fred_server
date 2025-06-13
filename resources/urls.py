# resources/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ResourceViewSet, ResourceCategoryViewSet, ResourceTagViewSet, resource_metrics

# Create router
router = DefaultRouter()

# Register viewsets with the router
# IMPORTANT: Empty string for main resources, then specific endpoints
router.register(r'categories', ResourceCategoryViewSet, basename='resourcecategory')  
router.register(r'tags', ResourceTagViewSet, basename='resourcetag')
router.register(r'', ResourceViewSet, basename='resource')  # This must come LAST

urlpatterns = [
    # Custom endpoint for metrics (must come before router URLs to avoid conflicts)
    path('resource_metrics/', resource_metrics, name='resource_metrics'),
    
    # Include all router URLs
    path('', include(router.urls)),
]

# This will create the following URL patterns:
# /api/resources/categories/ -> ResourceCategoryViewSet  
# /api/resources/tags/ -> ResourceTagViewSet
# /api/resources/ -> ResourceViewSet
# /api/resources/{id}/ -> ResourceViewSet detail
# /api/resources/resource_metrics/ -> resource_metrics function