from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AvailableOffersViewSet,
    AcceptOfferView,
    AcceptedOffersViewSet
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'available-offers', AvailableOffersViewSet, basename='available-offers')
router.register(r'accepted-offers', AcceptedOffersViewSet, basename='accepted-offers')


urlpatterns = [
    path('', include(router.urls)),
    path('accept-offer/', AcceptOfferView.as_view(), name='accept-offer'),
]