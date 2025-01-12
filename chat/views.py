from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatRoom.objects.filter(
            Q(client=user) | Q(admin=user)
        ).annotate(
            last_message_time=Max('messages__timestamp')
        ).order_by('-last_message_time')

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search for a chatroom by object_id.
        """
        object_id = request.query_params.get('object_id')
        
        logger.info(f"Searching chatroom by object_id: {object_id}")
        
        if not object_id:
            error_msg = "Missing required parameter: object_id"
            logger.error(error_msg)
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Move the Q objects into a filter
            chatroom = ChatRoom.objects.filter(
                Q(client=request.user) | Q(admin=request.user)
            ).get(object_id=object_id)
            
            logger.info(f"Found existing chatroom: {chatroom.id}")
            serializer = self.get_serializer(chatroom)
            return Response(serializer.data)
        except ChatRoom.DoesNotExist:
            error_msg = f"No chatroom found for object_id: {object_id}"
            logger.info(error_msg)
            return Response(
                {'error': error_msg},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            error_msg = f"Error searching for chatroom: {str(e)}"
            logger.error(error_msg)
            return Response(
                {'error': error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request, *args, **kwargs):
        object_id = request.data.get('object_id')
        other_user_id = request.data.get('user_id')

        logger.info(f"Creating chatroom - object_id: {object_id}, other_user_id: {other_user_id}")

        # Validate that object_id and other_user_id are provided
        if not object_id or not other_user_id:
            error_msg = "Both object_id and user_id are required"
            logger.error(error_msg)
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Dynamically determine content type from object_id
        content_type = self.get_content_type_from_object_id(object_id)
        if not content_type:
            error_msg = f"Invalid object ID or content type could not be determined for object_id: {object_id}"
            logger.error(error_msg)
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate the related object exists
        try:
            related_object = content_type.get_object_for_this_type(id=object_id)
        except ObjectDoesNotExist:
            error_msg = f"Object with ID {object_id} does not exist"
            logger.error(error_msg)
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate other user exists and has correct role
        try:
            other_user = User.objects.get(id=other_user_id)

            # Determine roles based on user types
            if request.user.is_client:
                if not other_user.is_admin:
                    error_msg = "Selected user must be an admin"
                    logger.error(error_msg)
                    return Response(
                        {'error': error_msg},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                client, admin = request.user, other_user
            elif request.user.is_admin:
                if not other_user.is_client:
                    error_msg = "Selected user must be a client"
                    logger.error(error_msg)
                    return Response(
                        {'error': error_msg},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                client, admin = other_user, request.user
            else:
                error_msg = "Invalid user roles"
                logger.error(error_msg)
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            error_msg = f"User with ID {other_user_id} does not exist"
            logger.error(error_msg)
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify permissions for the related object
        if not self.verify_chat_creation_permission(request.user, related_object):
            error_msg = "You do not have permission to create this chat room"
            logger.error(error_msg)
            return Response(
                {'error': error_msg},
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
            logger.info(f"Found existing chatroom: {existing_room.id}")
            serializer = self.get_serializer(existing_room)
            return Response(serializer.data, status=status.HTTP_200_OK)

        try:
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

            logger.info(f"Created new chatroom: {chat_room.id}")
            serializer = self.get_serializer(chat_room)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            error_msg = f"Error creating chatroom: {str(e)}"
            logger.error(error_msg)
            return Response(
                {'error': error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def verify_chat_creation_permission(self, user, related_object):
        """
        Verify if the user has permission to create a chat room for this object.
        """
        try:
            if hasattr(related_object, 'user'):
                return (
                    related_object.user == user or 
                    user.is_admin or 
                    user.is_staff
                )
            logger.warning(f"Object {related_object} has no user field")
            return False
        except Exception as e:
            logger.error(f"Error verifying chat creation permission: {str(e)}")
            return False

    def get_content_type_from_object_id(self, object_id):
        """
        Dynamically determine the content type based on the object_id.
        """
        try:
            # Check if object_id corresponds to SoftwareRequest model
            software_request = SoftwareRequest.objects.filter(id=object_id).first()
            if software_request:
                logger.info(f"Object {object_id} identified as SoftwareRequest")
                return ContentType.objects.get_for_model(SoftwareRequest)
            
            # Check if object_id corresponds to ResearchRequest model
            research_request = ResearchRequest.objects.filter(id=object_id).first()
            if research_request:
                logger.info(f"Object {object_id} identified as ResearchRequest")
                return ContentType.objects.get_for_model(ResearchRequest)
            
            # Check if object_id corresponds to Service model
            service = Service.objects.filter(id=object_id).first()
            if service:
                logger.info(f"Object {object_id} identified as Service")
                return ContentType.objects.get_for_model(Service)

            logger.error(f"No matching content type found for object_id: {object_id}")
            return None

        except Exception as e:
            logger.error(f"Error determining content type for object_id {object_id}: {str(e)}")
            return None