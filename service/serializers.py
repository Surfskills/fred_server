from rest_framework import serializers

from custom.models import IDManager
from .models import Service

class ServiceSerializer(serializers.ModelSerializer):
    # Add a shared_id field to expose the id_manager.id
    shared_id = serializers.IntegerField(source='id_manager.id', read_only=True)
    
    class Meta:
        model = Service
        fields = [
            'id',  # Keep the regular id field
            'shared_id',  # Add the shared id
            'user', 'title', 'description', 'cost', 
            'sizes', 'phone_number', 'delivery_time', 
            'support_duration', 'features', 'process_link', 
            'service_id', 'payment_status', 'order_status', 'acceptance_status',
        ]
        read_only_fields = ('id', 'shared_id')

    # Validate `features` to handle both strings and lists
    def validate_features(self, value):
        if isinstance(value, str):
            try:
                # Convert comma-separated string to a list
                return [item.strip() for item in value.split(',')]
            except Exception as e:
                raise serializers.ValidationError(f"Features parsing error: {e}")
        elif isinstance(value, list):
            return value
        else:
            raise serializers.ValidationError("Features must be a list or comma-separated string.")

    # Validate `sizes` structure
    def validate_sizes(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Sizes must be a dictionary.")
        
        expected_sizes = {'small', 'medium', 'large', 'extraLarge', 'doubleExtraLarge'}
        if not all(size in expected_sizes for size in value.keys()):
            raise serializers.ValidationError("Invalid size keys provided.")
        
        if not all(isinstance(count, int) for count in value.values()):
            raise serializers.ValidationError("Size quantities must be integers.")
        
        return value

    # Validate phone number format
    def validate_phone_number(self, value):
        if not value:
            return value
            
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if not (6 <= len(value) <= 15):
            raise serializers.ValidationError("Phone number length must be between 6 and 15 digits.")
        return value
        
    def create(self, validated_data):
        # Create a new IDManager instance to get a new primary key
        id_manager = IDManager.objects.create()
        validated_data['id_manager'] = id_manager
        
        # Set user if provided in context
        if self.context and 'request' in self.context:
            validated_data['user'] = self.context['request'].user
        
        return super().create(validated_data)
