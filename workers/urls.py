from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AvailableOffersViewSet,
    AcceptOfferView,
    AcceptedOffersViewSet,
    CompleteOfferView,
    ReturnOfferView,
    StartWorkOnOfferView
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'available-offers', AvailableOffersViewSet, basename='available-offers')
router.register(r'accepted-offers', AcceptedOffersViewSet, basename='accepted-offers')

urlpatterns = [
    # Include all the routes automatically created by the router
    path('', include(router.urls)),

    # Add the manually defined paths (e.g. for "return_offer" view)
    path('accept-offer/', AcceptOfferView.as_view(), name='accept-offer'),
    path('accepted-offers/<int:pk>/start_work/', StartWorkOnOfferView.as_view(), name='start_work_on_offer'),
    path('accepted-offers/<int:pk>/complete/', CompleteOfferView.as_view(), name='complete_offer'),
    path('accepted-offers/<int:pk>/return_offer/', ReturnOfferView.as_view(), name='return_offer'),  # Keep this separate
]
