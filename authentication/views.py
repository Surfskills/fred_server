# authentication/views.py
from django.utils.decorators import method_decorator
from django.contrib.auth import login, authenticate, logout as django_logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenVerifyView
from rest_framework_simplejwt.serializers import TokenVerifySerializer
from django.forms import ValidationError
from authentication.models import User
from authentication.serializers import SignInSerializer, SignUpSerializer, UserSerializer

# Token Authentication and Refresh token API view
class TokenAPIView(APIView):
    def post(self, request):
        # Get email and password from the request
        email = request.data.get('email')
        password = request.data.get('password')

        # Authenticate user
        user = authenticate(email=email, password=password)

        if user:
            # If user is authenticated, generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # Optionally, serialize user data
            user_data = UserSerializer(user).data

            return Response({
                'access': str(access_token),
                'refresh': str(refresh),
                'user': user_data,
            })
        else:
            return Response({'error': 'Invalid credentials'}, status=400)

# Unified authentication view (handles both signup and signin)
@method_decorator(csrf_exempt, name='dispatch')
class UnifiedAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Check if it's a sign-up request
        is_signup = request.data.get('is_signup', False)

        if is_signup:
            # Handle user registration
            signup_serializer = SignUpSerializer(data=request.data)
            if signup_serializer.is_valid():
                user = signup_serializer.save()

                # Create JWT tokens
                refresh = RefreshToken.for_user(user)

                # Django session login
                login(request, user)

                return Response({
                    'user': UserSerializer(user).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'User registered successfully'
                }, status=201)

            return Response(signup_serializer.errors, status=400)

        else:
            # Handle user sign-in (login)
            signin_serializer = SignInSerializer(data=request.data)

            try:
                signin_serializer.is_valid(raise_exception=True)
                user = signin_serializer.validated_data['user']

                # Create JWT tokens
                refresh = RefreshToken.for_user(user)

                # Django session login
                login(request, user)

                return Response({
                    'user': UserSerializer(user).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'Login successful'
                }, status=200)

            except ValidationError as e:
                return Response({
                    'error': str(e.detail)
                }, status=401)


# Logout view to blacklist the refresh token and log out the user
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Log out the user and blacklist the refresh token.
        """
        # Get the refresh token from the request (this is typically provided as part of the Authorization header or a separate field)
        refresh_token = request.data.get('refresh')  # assuming the token is passed in the request body

        if refresh_token:
            try:
                # Instantiate the RefreshToken from the token string
                token = RefreshToken(refresh_token)

                # Blacklist the refresh token
                token.blacklist()

            except Exception as e:
                return Response({'error': str(e)}, status=400)

        # Django session logout
        django_logout(request)

        return Response({"message": "Logged out successfully"}, status=200)


class VerifyTokenView(TokenVerifyView):
    """
    Takes a token and indicates if it is valid.
    Returns status 200 if token is valid, 401 if not.
    """
    serializer_class = TokenVerifySerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return Response({'detail': 'Token is valid'}, status=200)
        except Exception as e:
            return Response({'detail': 'Token is invalid or expired'}, status=401)

# Admin users list
class AdminListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get a list of admin users.
        """
        admins = User.objects.filter(is_staff=True)  # assuming 'is_staff' denotes admin role
        serializer = UserSerializer(admins, many=True)
        return Response(serializer.data, status=200)

# All users list
class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get a list of all users.
        """
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=200)
