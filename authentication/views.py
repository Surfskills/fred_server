import logging
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

# Set up a logger for this module
logger = logging.getLogger('authentication')

# Token Authentication and Refresh token API view
class TokenAPIView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        logger.info(f"Attempting to authenticate user: {email}")

        # Authenticate user
        user = authenticate(email=email, password=password)

        if user:
            logger.info(f"User {email} authenticated successfully.")

            # Generate JWT tokens
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
            logger.warning(f"Authentication failed for user: {email}")
            return Response({'error': 'Invalid credentials'}, status=400)

# Unified authentication view (handles both signup and signin)
import logging

# Get the 'authentication' logger defined in settings.py
logger = logging.getLogger('authentication')

class UnifiedAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Log incoming request data
        logger.debug(f"Received request data: {request.data}")

        is_signup = request.data.get('is_signup', False)
        logger.debug(f"Is this a sign-up request? {is_signup}")

        if is_signup:
            signup_serializer = SignUpSerializer(data=request.data)
            if signup_serializer.is_valid():
                user = signup_serializer.save()
                logger.info(f"User {user.email} registered successfully.")

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

            # Log errors if sign-up serializer fails
            logger.error(f"Sign-up failed. Validation errors: {signup_serializer.errors}")
            return Response({
                'error': 'Sign-up failed',
                'details': signup_serializer.errors
            }, status=400)

        else:
            signin_serializer = SignInSerializer(data=request.data)

            try:
                signin_serializer.is_valid(raise_exception=True)
                user = signin_serializer.validated_data['user']

                logger.info(f"User {user.email} signed in successfully.")

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
                logger.error(f"Sign-in failed. Validation error: {e.detail}")
                return Response({
                    'error': 'Sign-in failed',
                    'details': str(e.detail)
                }, status=400)


# Logout view to blacklist the refresh token and log out the user
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        logger.info(f"Attempting to log out. Refresh token: {refresh_token}")

        if refresh_token:
            try:
                # Instantiate the RefreshToken from the token string
                token = RefreshToken(refresh_token)

                # Blacklist the refresh token
                token.blacklist()

                logger.info(f"Refresh token {refresh_token} blacklisted.")

            except Exception as e:
                logger.error(f"Error blacklisting refresh token: {str(e)}")
                return Response({'error': str(e)}, status=400)

        # Django session logout
        django_logout(request)
        logger.info("User logged out successfully.")

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
            logger.info(f"Token {request.data['token']} is valid.")
            return Response({'detail': 'Token is valid'}, status=200)
        except Exception as e:
            logger.error(f"Token {request.data['token']} is invalid or expired. Error: {str(e)}")
            return Response({'detail': 'Token is invalid or expired'}, status=401)


# Admin users list
class AdminListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        admins = User.objects.filter(is_staff=True)  
        serializer = UserSerializer(admins, many=True)
        logger.info("Fetched list of admin users.")
        return Response(serializer.data, status=200)

# All users list
class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        logger.info("Fetched list of all users.")
        return Response(serializer.data, status=200)
