from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.RequestViewSet, basename='request')

urlpatterns = router.urls
