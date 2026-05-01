import logging
import uuid

from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.utils.decorators import method_decorator
from django.contrib.auth import login, authenticate, logout as django_logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from authentication.tokens import GigsHubRefreshToken
from tenancy.services import (
    build_auth_claims,
    merge_entitlement_flags,
    org_role_can_change_roles,
    org_role_can_manage_members,
    resolve_organization_role,
    set_exclusive_freelancer_tier_flag,
)
from uni_services.models import Freelancer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenVerifyView, TokenRefreshView
from authentication.models import User
from tenancy.models import Organization, OrganizationMembership, OrganizationRole
from authentication.serializers import (
    SignInSerializer, SignUpSerializer, UserSerializer,
    CustomTokenVerifySerializer, CustomTokenRefreshSerializer,
    PasswordResetSerializer, UserUpdateSerializer, ChangePasswordSerializer,
    CapabilityUpgradeSerializer,
)

# Set up a logger for this module
logger = logging.getLogger('authentication')

def _ensure_default_organization_for_user(user):
    """
    Create a first organization for users entering via the client hiring path.
    """
    existing = user.owned_organizations.order_by('created_at').first()
    if existing:
        return existing

    display = (user.get_full_name() or user.email.split('@')[0]).strip()
    base_slug = slugify(display) or f"user-{user.pk}"
    candidate = f"{base_slug}-org"
    idx = 2
    while Organization.objects.filter(slug=candidate).exists():
        candidate = f"{base_slug}-org-{idx}"
        idx += 1

    return Organization.objects.create(
        owner=user,
        name=f"{display} Organization",
        slug=candidate,
    )


class UnifiedAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.debug(f"Received request data: {request.data}")
        is_signup = bool(request.data.get('is_signup', False))
        action = (request.data.get('action') or '').lower()
        if action in ('register', 'signup'):
            is_signup = True
        elif action == 'login':
            is_signup = False
        logger.debug(f"Is this a sign-up request? {is_signup}")

        if is_signup:
            signup_serializer = SignUpSerializer(data=request.data)
            if signup_serializer.is_valid():
                user = signup_serializer.save()
                onboarding_intent = signup_serializer.validated_data.get('onboarding_intent') or 'work'
                auto_org = None
                is_client_signup = (
                    user.user_type == User.Types.CLIENT
                    or onboarding_intent in ('hire', 'both')
                )
                if user.user_type == User.Types.FREELANCER:
                    Freelancer.objects.get_or_create(user=user)
                    set_exclusive_freelancer_tier_flag(user, "native")
                if is_client_signup:
                    merge_entitlement_flags(user, {'client': True, 'organization': True})
                    auto_org = _ensure_default_organization_for_user(user)
                logger.info(f"User {user.email} registered successfully.")

                acting_org = request.data.get('acting_organization_id') or request.data.get('acting_org_id')
                if not acting_org and auto_org is not None:
                    acting_org = str(auto_org.id)
                try:
                    claims = build_auth_claims(user, acting_organization_id=acting_org or None, strict_org=bool(acting_org))
                except PermissionDenied as exc:
                    return Response({'detail': exc.detail}, status=403)
                refresh = GigsHubRefreshToken.for_user(user, acting_organization_id=acting_org)

                # Django session login
                login(request, user)

                return Response({
                    'user': UserSerializer(user, context={'auth_context': claims}).data,
                    'auth_context': claims,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'User registered successfully'
                }, status=201)

            logger.error(f"Sign-up failed. Validation errors: {signup_serializer.errors}")
            return Response({
                'error': 'Sign-up failed',
                'detail': 'Could not create account. Please review the form and try again.',
                'details': signup_serializer.errors
            }, status=400)

        else:
            signin_serializer = SignInSerializer(data=request.data)

            try:
                signin_serializer.is_valid(raise_exception=True)
                user = signin_serializer.validated_data['user']

                logger.info(f"User {user.email} signed in successfully.")

                acting_org = request.data.get('acting_organization_id') or request.data.get('acting_org_id')
                try:
                    claims = build_auth_claims(user, acting_organization_id=acting_org or None, strict_org=bool(acting_org))
                except PermissionDenied as exc:
                    return Response({'detail': exc.detail}, status=403)
                refresh = GigsHubRefreshToken.for_user(user, acting_organization_id=acting_org)

                # Django session login
                login(request, user)

                return Response({
                    'user': UserSerializer(user, context={'auth_context': claims}).data,
                    'auth_context': claims,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'Login successful'
                }, status=200)

            except ValidationError as e:
                logger.error(f"Sign-in failed. Validation error: {e.detail}")
                return Response({
                    'error': 'Sign-in failed',
                    'detail': 'Could not sign in. Check your email and password and try again.',
                    'details': e.detail
                }, status=400)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        logger.info(f"Attempting to log out user: {request.user.email}")

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info(f"Refresh token blacklisted for user: {request.user.email}")
            except Exception as e:
                logger.error(f"Error blacklisting refresh token: {str(e)}")
                return Response({'error': 'Failed to blacklist token'}, status=400)

        # Django session logout
        django_logout(request)
        logger.info(f"User {request.user.email} logged out successfully.")

        return Response({"message": "Logged out successfully"}, status=200)


class VerifyTokenView(TokenVerifyView):
    """
    Takes a token and indicates if it is valid.
    Returns status 200 if token is valid, 401 if not.
    """
    serializer_class = CustomTokenVerifySerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            token_value = request.data.get('token', '[TOKEN_VALUE]')
            logger.info(f"Token {token_value[:20]}... is valid.")
            return Response({'detail': 'Token is valid'}, status=200)
        except ValidationError as e:
            token_value = request.data.get('token', '[NOT_PROVIDED]')
            logger.error(f"Token validation failed for: {token_value[:20] if token_value != '[NOT_PROVIDED]' else token_value}. Validation errors: {e.detail}")
            
            if 'token' in e.detail and any('required' in str(error) for error in e.detail['token']):
                return Response({'detail': 'Token is required'}, status=400)
            else:
                return Response({'detail': 'Token is invalid or expired'}, status=401)
                
        except Exception as e:
            token_value = request.data.get('token', '[NOT_PROVIDED]')
            logger.error(f"Token verification error: {str(e)}")
            return Response({'detail': 'Token verification failed'}, status=401)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Takes a refresh token and returns a new access token.
    """
    serializer_class = CustomTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            refresh_token = request.data.get('refresh', '[NOT_PROVIDED]')
            logger.info(f"Successfully refreshed token for refresh token: {refresh_token[:20]}...")
            return Response(serializer.validated_data, status=200)
        except ValidationError as e:
            refresh_token = request.data.get('refresh', '[NOT_PROVIDED]')
            logger.error(f"Token refresh failed for: {refresh_token[:20] if refresh_token != '[NOT_PROVIDED]' else refresh_token}. Errors: {e.detail}")
            return Response({'detail': 'Token refresh failed'}, status=401)
        except Exception as e:
            refresh_token = request.data.get('refresh', '[NOT_PROVIDED]')
            logger.error(f"Token refresh error: {str(e)}")
            return Response({'detail': 'Token refresh failed'}, status=401)


class PasswordResetView(APIView):
    """
    Request password reset email
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data['email']
            # Here you would implement your password reset email logic
            logger.info(f"Password reset requested for email: {email}")
            return Response({'message': 'Password reset email sent'}, status=200)
        except ValidationError as e:
            logger.error(f"Password reset request failed: {e.detail}")
            return Response(
                {
                    'error': 'Password reset request failed',
                    'detail': 'Could not send reset link. Please verify your email and try again.',
                    'details': e.detail,
                },
                status=400,
            )


class SwitchContextView(APIView):
    """
    Switch JWT tenant (personal user vs organization you belong to — owner, admin, or member).
    Body: {"acting_organization_id": "<uuid>" | null}
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        missing = object()
        raw = request.data.get('acting_organization_id', missing)
        if raw is missing:
            raw = request.data.get('acting_org_id', missing)
        if raw is missing:
            return Response(
                {'acting_organization_id': ['Required: send null for personal tenant or an organization UUID.']},
                status=400,
            )

        if raw in (None, '', 'null'):
            claims = build_auth_claims(request.user, acting_organization_id=None)
            refresh = GigsHubRefreshToken.for_user(request.user, acting_organization_id=None)
            return Response({
                'auth_context': claims,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(request.user, context={'auth_context': claims}).data,
            })

        try:
            oid = uuid.UUID(str(raw))
        except ValueError:
            return Response({'acting_organization_id': ['Invalid UUID.']}, status=400)

        acting_org = str(oid)
        try:
            claims = build_auth_claims(request.user, acting_organization_id=acting_org, strict_org=True)
        except PermissionDenied as exc:
            return Response({'detail': exc.detail}, status=403)

        refresh = GigsHubRefreshToken.for_user(request.user, acting_organization_id=acting_org)
        return Response({
            'auth_context': claims,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(request.user, context={'auth_context': claims}).data,
        })


class UserOrganizationsView(APIView):
    """Organizations the user owns or belongs to (for tenant switcher)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Q
        from tenancy.models import Organization

        orgs = (
            Organization.objects.filter(Q(owner=request.user) | Q(memberships__user=request.user))
            .distinct()
            .order_by('name')
        )
        data = [{'id': str(o.id), 'name': o.name, 'slug': o.slug} for o in orgs]
        return Response({'organizations': data})


class OrganizationMembershipListCreateView(APIView):
    """GET: list members (org owner or org admin). POST: add user by email — owner or admin."""

    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = get_object_or_404(Organization, pk=organization_id)
        my_role = resolve_organization_role(request.user, org)
        if my_role is None:
            return Response({'detail': 'Not a member of this organization.'}, status=403)
        if not org_role_can_manage_members(my_role):
            return Response({'detail': 'Insufficient organization permissions.'}, status=403)

        rows = (
            OrganizationMembership.objects.filter(organization_id=org.pk)
            .select_related('user')
            .order_by('role', 'user__email')
        )
        members = [{'user_id': m.user_id, 'email': m.user.email, 'role': m.role} for m in rows]
        return Response({'organization_id': str(org.pk), 'members': members})

    def post(self, request, organization_id):
        org = get_object_or_404(Organization, pk=organization_id)
        actor_role = resolve_organization_role(request.user, org)
        if actor_role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
            return Response({'detail': 'Only organization owner/admin can add members.'}, status=403)

        email = (request.data.get('email') or '').strip()
        role_raw = (request.data.get('role') or 'member').strip().lower()
        if not email:
            return Response({'email': ['Required.']}, status=400)
        if role_raw not in ('member', 'admin', 'support'):
            return Response({'role': ['Must be member, admin, or support.']}, status=400)
        if actor_role == OrganizationRole.ADMIN and role_raw != 'support':
            return Response(
                {'detail': 'Organization admins can only add support members.'},
                status=403,
            )

        try:
            invite_role = OrganizationRole(role_raw)
        except ValueError:
            return Response({'role': ['Invalid role.']}, status=400)

        target = User.objects.filter(email__iexact=email).first()
        if not target:
            return Response({'detail': 'No user registered with this email.'}, status=404)
        if target.pk == org.owner_id:
            return Response({'detail': 'User is already the organization owner.'}, status=400)

        OrganizationMembership.objects.update_or_create(
            organization=org,
            user=target,
            defaults={'role': invite_role.value},
        )
        return Response(
            {'detail': 'Member saved.', 'email': target.email, 'role': invite_role.value},
            status=201,
        )


class OrganizationMembershipDetailView(APIView):
    """PATCH member role (`admin` | `member` | `support`). Owner/admin with scoped permissions."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, organization_id, member_user_id):
        org = get_object_or_404(Organization, pk=organization_id)
        actor_role = resolve_organization_role(request.user, org)
        if not org_role_can_change_roles(actor_role):
            return Response({'detail': 'Only organization owner/admin can change roles.'}, status=403)

        membership = get_object_or_404(
            OrganizationMembership.objects.select_related('user'),
            organization_id=org.pk,
            user_id=member_user_id,
        )
        if membership.role == OrganizationRole.OWNER.value:
            return Response({'detail': 'Cannot change owner membership via API.'}, status=400)

        role_raw = (request.data.get('role') or '').strip().lower()
        if role_raw not in ('admin', 'member', 'support'):
            return Response({'role': ['Must be admin, member, or support.']}, status=400)
        if actor_role == OrganizationRole.ADMIN:
            if membership.role in (OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value):
                return Response(
                    {'detail': 'Organization admins cannot modify owner/admin memberships.'},
                    status=403,
                )
            if role_raw != 'support':
                return Response(
                    {'detail': 'Organization admins can only assign support role.'},
                    status=403,
                )

        membership.role = OrganizationRole(role_raw).value
        membership.save(update_fields=['role', 'updated_at'])
        return Response(
            {
                'detail': 'Updated.',
                'user_id': membership.user_id,
                'email': membership.user.email,
                'role': membership.role,
            }
        )


class OrganizationCreateView(APIView):
    """Create an organization owned by current user."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        slug = (request.data.get('slug') or '').strip()
        if not name:
            return Response({'name': ['Required.']}, status=400)
        if not slug:
            return Response({'slug': ['Required.']}, status=400)
        if Organization.objects.filter(slug=slug).exists():
            return Response({'slug': ['Already exists.']}, status=400)

        org = Organization.objects.create(owner=request.user, name=name, slug=slug)
        merge_entitlement_flags(request.user, {'native': True, 'organization': True})

        return Response(
            {
                'organization': {'id': str(org.id), 'name': org.name, 'slug': org.slug},
                'detail': 'Organization created successfully.',
            },
            status=201,
        )


class CapabilityUpgradeView(APIView):
    """Upgrade current account capabilities and return refreshed auth context."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CapabilityUpgradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        capability = serializer.validated_data['capability']

        if capability == 'client':
            merge_entitlement_flags(request.user, {'client': True})
        elif capability == 'support':
            merge_entitlement_flags(request.user, {'support': True})
        elif capability == 'admin':
            merge_entitlement_flags(request.user, {'admin': True})
        elif capability in ('native', 'dynamic', 'demer'):
            if not getattr(request.user, 'is_freelancer', False):
                return Response({'detail': 'Only freelancer accounts can upgrade marketplace tiers.'}, status=403)
            try:
                freelancer = request.user.freelancer_profile
            except Freelancer.DoesNotExist:
                freelancer = Freelancer.objects.create(user=request.user)
            tier_rank = {'native': 0, 'dynamic': 1, 'demer': 2}
            if tier_rank[capability] < tier_rank[freelancer.marketplace_tier]:
                return Response({'detail': 'Cannot downgrade marketplace tier.'}, status=400)
            freelancer.marketplace_tier = capability
            freelancer.save(update_fields=['marketplace_tier'])
            set_exclusive_freelancer_tier_flag(request.user, capability)

        claims = build_auth_claims(request.user, acting_organization_id=None)
        refresh = GigsHubRefreshToken.for_user(request.user, acting_organization_id=None)
        return Response(
            {
                'auth_context': claims,
                'user': UserSerializer(request.user, context={'auth_context': claims}).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'detail': f'{capability} capability enabled.',
            }
        )


class RecruiterTeamListView(APIView):
    """
    Freelancers this user has recruited (accepted project workspace invites add rows to RecruitedFreelancer).
    Used by the client hub dashboard and My team — same roster for personal or organization posting context.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from tenancy.models import RecruitedFreelancer

        qs = (
            RecruitedFreelancer.objects.filter(recruiter=request.user)
            .select_related('freelancer', 'freelancer__user')
            .order_by('-created_at')
        )
        recruits = []
        for link in qs:
            f = link.freelancer
            u = f.user
            display = f.display_name or (u.get_full_name() or '').strip() or u.email
            recruits.append(
                {
                    'id': str(f.id),
                    'display_name': display,
                    'email': u.email,
                    'freelancer_type': f.freelancer_type,
                    'freelancer_type_display': f.get_freelancer_type_display(),
                    'experience_level': f.experience_level,
                    'experience_level_display': f.get_experience_level_display(),
                    'availability_status': f.availability_status,
                    'average_rating': float(f.average_rating) if getattr(f, 'average_rating', None) is not None else None,
                    'recruited_at': link.created_at.isoformat(),
                }
            )

        return Response({'recruits': recruits, 'total': len(recruits)})


class CollaborationPeersView(APIView):
    """
    Freelancers who share at least one client's roster with you — typically after accepting organization invites.

    Implemented via tenancy.RecruitedFreelancer: accepting a project invite adds you to that client's recruits.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from tenancy.models import RecruitedFreelancer as RF
        from uni_services.models import Freelancer as Fl

        if not getattr(request.user, 'is_freelancer', False):
            return Response({'detail': 'Freelancers only.'}, status=403)

        try:
            me = Fl.objects.get(user=request.user)
        except Fl.DoesNotExist:
            return Response({'clients': [], 'peers': []})

        recruiter_ids = list(RF.objects.filter(freelancer=me).values_list('recruiter_id', flat=True).distinct())
        if not recruiter_ids:
            return Response({'clients': [], 'peers': []})

        recruiter_users = User.objects.filter(id__in=recruiter_ids).only('id', 'email')
        clients = [{'id': u.id, 'email': u.email} for u in recruiter_users]

        peer_ids = (
            RF.objects.filter(recruiter_id__in=recruiter_ids)
            .exclude(freelancer_id=me.pk)
            .values_list('freelancer_id', flat=True)
            .distinct()
        )
        peers_qs = (
            Fl.objects.filter(pk__in=peer_ids)
            .select_related('user')
            .order_by('display_name')
        )

        peers = []
        for f in peers_qs:
            peers.append(
                {
                    'id': str(f.id),
                    'display_name': f.display_name or (f.user.get_full_name() or f.user.email),
                    'email': f.user.email,
                    'freelancer_type': f.freelancer_type,
                    'freelancer_type_display': f.get_freelancer_type_display(),
                    'experience_level': f.experience_level,
                    'experience_level_display': f.get_experience_level_display(),
                    'availability_status': f.availability_status,
                    'average_rating': float(f.average_rating) if getattr(f, 'average_rating', None) is not None else None,
                }
            )

        return Response({'clients': clients, 'peers': peers})


class UserProfileView(APIView):
    """
    Get and update user profile
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            logger.info(f"User profile updated for: {user.email}")
            return Response(UserSerializer(user).data)
        except ValidationError as e:
            logger.error(f"Profile update failed for user {request.user.email}: {e.detail}")
            return Response({'error': 'Profile update failed', 'details': e.detail}, status=400)


class ChangePasswordView(APIView):
    """
    Change user password
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            logger.info(f"Password changed for user: {user.email}")
            return Response({'message': 'Password changed successfully'}, status=200)
        except ValidationError as e:
            logger.error(f"Password change failed for user {request.user.email}: {e.detail}")
            return Response({'error': 'Password change failed', 'details': e.detail}, status=400)


# Admin and User list views (unchanged)
class AdminListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        admins = User.objects.filter(is_staff=True)  
        serializer = UserSerializer(admins, many=True)
        logger.info("Fetched list of admin users.")
        return Response(serializer.data, status=200)


class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        logger.info("Fetched list of all users.")
        return Response(serializer.data, status=200)