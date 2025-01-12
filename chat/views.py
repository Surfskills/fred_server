from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Max
from django.contrib.contenttypes.models import ContentType
from authentication.models import User
from .serializers import ChatRoomSerializer
from .models import ChatRoom, Message



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
    # permission_classes = [permissions.IsAuthenticated, IsAdminOrClientOwner]

    def get_queryset(self):
        user = self.request.user
        return ChatRoom.objects.filter(
            Q(client=user) | Q(admin=user)
        ).annotate(
            last_message_time=Max('messages__timestamp')
        ).order_by('-last_message_time')

    def create(self, request, *args, **kwargs):
        content_type_id = request.data.get('content_type')
        object_id = request.data.get('object_id')
        other_user_id = request.data.get('user_id')

        # Validate content type
        try:
            content_type = ContentType.objects.get_for_id(content_type_id)
        except ContentType.DoesNotExist:
            return Response(
                {'error': 'Invalid content type'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate the related object exists
        try:
            related_object = content_type.get_object_for_this_type(id=object_id)
        except:
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

        # Create new chat room
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