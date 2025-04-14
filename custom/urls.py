# In your app's urls.py (e.g., requests/urls.py)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RequestViewSet

router = DefaultRouter()
# We don't register the viewset with the router normally since it's a ViewSet (not ModelViewSet)
# Instead, we'll manually define the URLs

urlpatterns = [
    path('', RequestViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='request-list'),
    
    path('<str:shared_id>/', RequestViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'update',
        'delete': 'destroy'
    }), name='request-detail'),
    
    path('software/', RequestViewSet.as_view({
        'get': 'software'
    }), name='request-software'),
    
    path('research/', RequestViewSet.as_view({
        'get': 'research'
    }), name='request-research'),
]

# If you want to include these in your project's main urls.py:
# from django.urls import path, include
# urlpatterns = [
#     path('api/requests/', include('requests.urls')),
#     ...
# ]