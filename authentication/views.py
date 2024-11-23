from django.forms import ValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, logout

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SignInSerializer, SignUpSerializer, UserSerializer

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


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)  # End the Django session for the user
        return Response({
            'message': 'Successfully logged out'
        }, status=status.HTTP_200_OK)
    

class SessionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'user': {
                'id': user.id,

                'email': user.email,

            },
            'jwt_token': request.auth  # Include the JWT token if needed
        })