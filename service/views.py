from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from authentication.models import User
from .models import Service
from .serializers import ServiceSerializer
from django.shortcuts import get_object_or_404


class ServiceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        services = Service.objects.all()
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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


class ServiceDetailView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """
        Retrieve a specific service by its ID.
        """
        service = get_object_or_404(Service, pk=pk)
        serializer = ServiceSerializer(service)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        """
        Partially update a service, allowing updates only to `cost`, `payment_status`, or `order_status`.
        """
        service = get_object_or_404(Service, pk=pk)
        data = request.data
        
        # Only update the allowed fields: cost, payment_status, or order_status
        allowed_fields = ['cost', 'payment_status', 'order_status']
        
        for field in allowed_fields:
            if field in data:
                setattr(service, field, data[field])

        service.save()
        serializer = ServiceSerializer(service)
        return Response(serializer.data, status=status.HTTP_200_OK)