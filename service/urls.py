from django.urls import path
from .views import ServiceCreateView, ServiceDetailView, ServiceListView

urlpatterns = [
    # Service creation (POST request)
    path('', ServiceCreateView.as_view(), name='service-create'),
    
    # Service listing (GET request)
    path('list/', ServiceListView.as_view(), name='service-list'),  # New URL for listing services
    
    # Service detail (GET and PATCH requests)
    path('<int:pk>/', ServiceDetailView.as_view(), name='service-detail'),
]
