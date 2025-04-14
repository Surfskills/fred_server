from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RequestViewSet

router = DefaultRouter()
router.register(r'requests', RequestViewSet, basename='request')

# Manually add URL for shared_id
urlpatterns = [
    path('requests/<str:shared_id>/', RequestViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}), name='request-detail'),
    path('', include(router.urls)),
]
