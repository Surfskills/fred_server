from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from authentication.models import User
from .models import Service
from .serializers import ServiceSerializer
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
import uuid

class ServiceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only return services owned by the current user
        services = Service.objects.filter(user=request.user)
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ServiceCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data['user'] = request.user.id
        user = request.user
        service_id = data.get('service_id')
        title = data.get('title')

        # Validate if service with the same service_id exists for this user
        if service_id:
            existing_service = Service.objects.filter(service_id=service_id, user=user).first()
            if existing_service:
                return Response(
                    {
                        "message": "Service with this service ID already exists.",
                        "service_id": existing_service.id,
                        "service_details": ServiceSerializer(existing_service).data,
                    },
                    status=status.HTTP_200_OK,
                )

        # Check if a service with the same title and user exists
        if title:
            existing_title_service = Service.objects.filter(
                user=user,
                title=title
            ).first()
            if existing_title_service:
                return Response(
                    {
                        "message": "Service with this title already exists.",
                        "service_id": existing_title_service.id,
                        "service_details": ServiceSerializer(existing_title_service).data,
                    },
                    status=status.HTTP_200_OK,
                )

        # Generate a unique service_id if not provided
        if not service_id:
            data['service_id'] = f"svc-{str(uuid.uuid4())[:8]}"
            
        serializer = ServiceSerializer(data=data)
        if serializer.is_valid():
            # Django will handle the automatic primary key (id) generation
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_user_service(self, pk, user):
        """
        Helper method to get a service that belongs to the user
        """
        service = get_object_or_404(Service, pk=pk)
        if service.user != user:
            raise PermissionDenied("You do not have permission to access this service.")
        return service

    def get(self, request, pk):
        """
        Retrieve a specific service by its ID, ensuring it belongs to the current user.
        """
        service = self.get_user_service(pk, request.user)
        serializer = ServiceSerializer(service)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        """
        Partially update a service, ensuring it belongs to the current user.
        """
        service = self.get_user_service(pk, request.user)
        data = request.data
        
        # Only update the allowed fields
        allowed_fields = ['cost', 'payment_status', 'order_status']
        
        for field in allowed_fields:
            if field in data:
                setattr(service, field, data[field])

        service.save()
        serializer = ServiceSerializer(service)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        """
        Delete a specific service by its ID, ensuring it belongs to the current user.
        """
        service = self.get_user_service(pk, request.user)

        # Check if the service has a paid payment status
        if service.payment_status == 'paid':
            raise PermissionDenied("You cannot delete an order that has been paid.")

        # If the payment status is not paid, proceed with deletion
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)