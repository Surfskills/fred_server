# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    admin_dashboard, freelancer_stats, 
    BaseServiceViewSet, SoftwareServiceViewSet, 
    ResearchServiceViewSet, CustomServiceViewSet, 
    ServiceFileViewSet, BidViewSet
)

router = DefaultRouter()

# Main service management
router.register(r'services', BaseServiceViewSet, basename='baseservice')

# Specialized service views (read-only)
router.register(r'software-services', SoftwareServiceViewSet, basename='softwareservice')
router.register(r'research-services', ResearchServiceViewSet, basename='researchservice')
router.register(r'custom-services', CustomServiceViewSet, basename='customservice')

# File management
router.register(r'service-files', ServiceFileViewSet, basename='servicefile')

# Bid management
router.register(r'bids', BidViewSet, basename='bid')

urlpatterns = [
    path('', include(router.urls)),
    
    # Admin dashboard endpoints (simple views)
    path('admin-dashboard/', admin_dashboard, name='admin-dashboard'),
    path('admin-dashboard/freelancer-stats/', freelancer_stats, name='freelancer-stats'),
]