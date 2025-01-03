from django.forms import ValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout as django_logout
from .serializers import SignInSerializer, SignUpSerializer, UserSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.views import TokenVerifyView
from rest_framework_simplejwt.serializers import TokenVerifySerializer

# Token Authentication and Refresh token API view
class TokenAPIView(APIView):
    def post(self, request):
        # Get username and password from the request
        username = request.data.get('username')
        password = request.data.get('password')

        # Authenticate user
        user = authenticate(username=username, password=password)

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
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


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
                }, status=status.HTTP_201_CREATED)

            return Response(signup_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                }, status=status.HTTP_200_OK)

            except ValidationError as e:
                return Response({
                    'error': str(e.detail)
                }, status=status.HTTP_401_UNAUTHORIZED)


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
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Django session logout
        django_logout(request)

        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)


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
            return Response({'detail': 'Token is valid'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': 'Token is invalid or expired'}, status=status.HTTP_401_UNAUTHORIZED)
