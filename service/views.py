from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
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

        # Extract user and other fields
        data['user'] = request.user.id
        user = request.user
        service_id = data.get('service_id')
        title = data.get('title')

        # Validate if service with the same service_id exists
        existing_service = Service.objects.filter(service_id=service_id).first()
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
        existing_title_service = Service.objects.filter(user=user, title=title).first()
        if existing_title_service:
            return Response(
                {
                    "message": "Service with this title already exists.",
                    "service_id": existing_title_service.id,
                    "service_details": ServiceSerializer(existing_title_service).data,
                },
                status=status.HTTP_200_OK,
            )

        # Proceed to create a new service
        serializer = ServiceSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=user)  # Attach the user
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # Handle validation errors
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