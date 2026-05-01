# authentication/urls.py
from django.urls import path
from .views import (
    UnifiedAuthView,
    LogoutView,
    VerifyTokenView,
    CustomTokenRefreshView,
    PasswordResetView,
    UserProfileView,
    ChangePasswordView,
    AdminListView,
    UserListView,
    SwitchContextView,
    UserOrganizationsView,
    OrganizationMembershipListCreateView,
    OrganizationMembershipDetailView,
    OrganizationCreateView,
    CapabilityUpgradeView,
    CollaborationPeersView,
    RecruiterTeamListView,
)

urlpatterns = [
    # Authentication endpoints
    path('auth/', UnifiedAuthView.as_view(), name='unified_auth'),  # For both login and signup
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Token management
    path('auth/verify/', VerifyTokenView.as_view(), name='token_verify'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    
    # Password reset
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),
    
    # Tenancy / session
    path('context/', SwitchContextView.as_view(), name='switch_context'),
    path('organizations/', UserOrganizationsView.as_view(), name='user_organizations'),
    path('organizations/create/', OrganizationCreateView.as_view(), name='organization_create'),
    path('organizations/<uuid:organization_id>/members/', OrganizationMembershipListCreateView.as_view()),
    path(
        'organizations/<uuid:organization_id>/members/<int:member_user_id>/',
        OrganizationMembershipDetailView.as_view(),
    ),
    path('my-team/', RecruiterTeamListView.as_view(), name='recruiter_team'),
    path('collaboration-peers/', CollaborationPeersView.as_view(), name='collaboration_peers'),
    path('capabilities/upgrade/', CapabilityUpgradeView.as_view(), name='capability_upgrade'),

    # User profile
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Admin endpoints
    path('admins/', AdminListView.as_view(), name='admin_list'),
    path('users/', UserListView.as_view(), name='user_list'),
]