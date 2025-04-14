from django.http import Http404
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
        title = data.get('title')

        # Check if a service with the same title exists for this user
        if title:
            existing_title_service = Service.objects.filter(
                user=user,
                title=title
            ).first()
            if existing_title_service:
                return Response(
                    {
                        "message": "You already have a service with this title.",
                        "service_id": existing_title_service.id,
                        "service_details": ServiceSerializer(existing_title_service).data,
                    },
                    status=status.HTTP_200_OK,
                )

        serializer = ServiceSerializer(data=data)
        if serializer.is_valid():
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

def delete(self, request, shared_id):
    """
    Delete a specific service by its shared_id, ensuring it belongs to the current user.
    """
    try:
        # Get the service using shared_id instead of primary key
        service = Service.objects.get(shared_id=shared_id, user=request.user)
    except Service.DoesNotExist:
        raise Http404("Service not found or you don't have permission to delete it.")

    # Check if the service has a paid payment status
    if service.payment_status == 'paid':
        raise PermissionDenied("You cannot delete an order that has been paid.")

    # If the payment status is not paid, proceed with deletion
    service.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)