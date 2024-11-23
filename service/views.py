
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from authentication.models import User
from .serializers import ServiceSerializer

class ServiceCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        data = request.data.copy()

        # Map `user_id` to `user`
        user_id = data.pop('user_id', None)
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"error": "Invalid user ID."}, status=status.HTTP_400_BAD_REQUEST)

        data['user'] = user.id  # Attach the user to the service

        serializer = ServiceSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=user)  # Save with the user
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)