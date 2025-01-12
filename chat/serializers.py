from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import ChatRoom, Message

class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'content', 'sender_id', 'sender_email',
            'timestamp', 'is_read', 'read_at', 'attachment'
        ]

class ChatRoomSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    client_email = serializers.EmailField(source='client.email', read_only=True)
    admin_email = serializers.EmailField(source='admin.email', read_only=True)
    latest_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'client', 'client_email', 'admin', 'admin_email',
            'content_type', 'object_id', 'created_at', 'updated_at',
            'is_active', 'messages', 'latest_message', 'unread_count'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_latest_message(self, obj):
        latest = obj.messages.first()
        if latest:
            return MessageSerializer(latest).data
        return None

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()