# resources/tag_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ResourceTagViewSet

router = DefaultRouter()
router.register(r'', ResourceTagViewSet, basename='resourcetag')

urlpatterns = [
    path('', include(router.urls)),
]