from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from authentication.models import User
from .serializers import ChatRoomSerializer
from .models import ChatRoom, Message
from django.core.exceptions import ObjectDoesNotExist
from service.models import Service
from custom.models import SoftwareRequest, ResearchRequest
from django.db.models import Q, Max
import logging

# Set up logger for debugging
logger = logging.getLogger(__name__)

class IsAdminOrClientOwner(permissions.BasePermission):
    """
    Custom permission to only allow admins full access and clients access to their own chats.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin:
            return True
        return obj.client == request.user


class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    # permission_classes = [permissions.IsAuthenticated, IsAdminOrClientOwner]  # You can enable this if needed

    def get_queryset(self):
        user = self.request.user
        return ChatRoom.objects.filter(
            Q(client=user) | Q(admin=user)
        ).annotate(
            last_message_time=Max('messages__timestamp')
        ).order_by('-last_message_time')

    def create(self, request, *args, **kwargs):
        object_id = request.data.get('object_id')
        other_user_id = request.data.get('user_id')

        # Validate that object_id and other_user_id are provided
        if not object_id or not other_user_id:
            return Response(
                {'error': 'Both object_id and user_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Dynamically determine content type from object_id
        content_type = self.get_content_type_from_object_id(object_id)
        if not content_type:
            return Response(
                {'error': 'Invalid object ID or content type could not be determined'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate the related object exists
        try:
            related_object = content_type.get_object_for_this_type(id=object_id)
        except ObjectDoesNotExist:
            return Response(
                {'error': 'Invalid object ID'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate other user exists and has correct role
        try:
            other_user = User.objects.get(id=other_user_id)

            # Determine roles based on user types
            if request.user.is_client:
                if not other_user.is_admin:
                    return Response(
                        {'error': 'Selected user must be an admin'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                client, admin = request.user, other_user
            elif request.user.is_admin:
                if not other_user.is_client:
                    return Response(
                        {'error': 'Selected user must be a client'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                client, admin = other_user, request.user
            else:
                return Response(
                    {'error': 'Invalid user roles'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid user ID'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify permissions for the related object
        if not self.verify_chat_creation_permission(request.user, related_object):
            return Response(
                {'error': 'You do not have permission to create this chat room'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if chat room already exists
        existing_room = ChatRoom.objects.filter(
            content_type=content_type,
            object_id=object_id,
            client=client,
            admin=admin
        ).first()

        if existing_room:
            serializer = self.get_serializer(existing_room)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Create new chat room if not found
        chat_room = ChatRoom.objects.create(
            content_type=content_type,
            object_id=object_id,
            client=client,
            admin=admin
        )

        # Create initial system message
        Message.objects.create(
            room=chat_room,
            sender=request.user,
            content=f"Chat room created by {request.user.email}",
            is_read=True
        )

        serializer = self.get_serializer(chat_room)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def verify_chat_creation_permission(self, user, related_object):
        """
        Verify if the user has permission to create a chat room for this object.
        """
        if hasattr(related_object, 'user'):
            return (
                related_object.user == user or 
                user.is_admin or 
                user.is_staff
            )
        return False

    def get_content_type_from_object_id(self, object_id):
        """
        Dynamically determine the content type based on the object_id.
        Checks if the object_id corresponds to SoftwareRequest, ResearchRequest, or Service.
        """
        try:
            # Check if object_id corresponds to SoftwareRequest model
            software_request = SoftwareRequest.objects.filter(id=object_id).first()
            if software_request:
                return ContentType.objects.get_for_model(SoftwareRequest)
            
            # Check if object_id corresponds to ResearchRequest model
            research_request = ResearchRequest.objects.filter(id=object_id).first()
            if research_request:
                return ContentType.objects.get_for_model(ResearchRequest)
            
            # Check if object_id corresponds to Service model
            service = Service.objects.filter(id=object_id).first()
            if service:
                return ContentType.objects.get_for_model(Service)

            return None

        except Exception as e:
            logger.error(f"Error determining content type for object_id {object_id}: {e}")
            return None
