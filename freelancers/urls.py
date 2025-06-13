from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FreelancerViewSet

router = DefaultRouter()
router.register(r'', FreelancerViewSet, basename='freelancer')

urlpatterns = [
    path('', include(router.urls)),
    
    # Additional endpoints
    path('freelancers/search/', FreelancerViewSet.as_view({'get': 'search'}), name='freelancer-search'),
    path('freelancers/stats/', FreelancerViewSet.as_view({'get': 'stats'}), name='freelancer-stats'),
    path('freelancers/top-rated/', FreelancerViewSet.as_view({'get': 'top_rated'}), name='freelancer-top-rated'),
    path('freelancers/recently-joined/', FreelancerViewSet.as_view({'get': 'recently_joined'}), name='freelancer-recently-joined'),
    path('freelancers/my_profile/', FreelancerViewSet.as_view({'get': 'my_profile'}), name='freelancer-my-profile'),
    path('freelancers/dashboard_stats/', FreelancerViewSet.as_view({'get': 'dashboard_stats'}), name='freelancer-dashboard'),
]