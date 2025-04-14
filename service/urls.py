# In your app's urls.py (e.g., services/urls.py)
from django.urls import path
from .views import ServiceListView, ServiceCreateView, ServiceDetailView

urlpatterns = [
    # GET all services for current user
    path('', ServiceListView.as_view(), name='service-list'),
    
    # POST to create a new service
    path('create/', ServiceCreateView.as_view(), name='service-create'),
    
    # GET/PATCH/DELETE a specific service by shared_id
    path('<str:shared_id>/', ServiceDetailView.as_view(), name='service-detail'),
]

# Then in your project's main urls.py, include these URLs:
# from django.urls import path, include
# urlpatterns = [
#     path('api/services/', include('services.urls')),
#     ...
# ]