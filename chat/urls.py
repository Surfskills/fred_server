# chat/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet

# Create a router and register our viewset with it.
router = DefaultRouter()
router.register(r'chatrooms', ChatRoomViewSet, basename='chatroom')

# The URLs for the viewset will be automatically generated
urlpatterns = [
    path('', include(router.urls)),  # Register all routes
]
