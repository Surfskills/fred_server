from django.urls import path
from .views import ServiceCreateView, ServiceDetailView, ServiceListView

urlpatterns = [
    # Service creation (POST request)
    path('', ServiceCreateView.as_view(), name='service-create'),
    
    # Service listing (GET request)
    path('list/', ServiceListView.as_view(), name='service-list'),
    
    # Service detail (GET, PATCH, DELETE requests using the global primary key)
    path('<int:pk>/', ServiceDetailView.as_view(), name='service-detail'),
]
