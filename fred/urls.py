"""
URL configuration for fred project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Gigs Hub API",
        default_version="v1",
        description="API documentation for the Gigs Hub backend services.",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    # path('api/service/', include('service.urls')),
    path('api/chat/', include('chat.urls')),
    path('api/freelancers/', include('freelancers.urls')),
    path('api/uni_services/', include('uni_services.urls')),
    path('api/resources/', include('resources.urls')),
    path('api/', include('documents_management.urls')),
    path('api/support/', include('support.urls')),
    path('api/payouts/', include('payouts.urls')),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc-ui'),
    path('api/openapi.json', schema_view.without_ui(cache_timeout=0), name='openapi-schema'),
]