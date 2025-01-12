# authentication/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from authentication.views import AdminListView, LogoutView, TokenAPIView, UnifiedAuthView, UserListView, VerifyTokenView


urlpatterns = [

    path('auth/', UnifiedAuthView.as_view(), name='unified-auth'),
    path('token/', TokenAPIView.as_view(), name='token_api'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify/', VerifyTokenView.as_view(), name='token_verify'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('admins/', AdminListView.as_view(), name='admin-list'),
]
