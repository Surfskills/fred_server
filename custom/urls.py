from django.urls import path, include
from rest_framework.routers import DefaultRouter
from custom.views import RequestViewSet

router = DefaultRouter()
router.register(r'requests', RequestViewSet, basename='request')

urlpatterns = [
    path('', include(router.urls)),
]
