import uuid
from rest_framework import serializers
from models import Service

class ServiceSerializer(serializers.ModelSerializer):
    shared_id = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Service
        fields = [
            'id',
            'shared_id',
            'user', 
            'title', 
            'description', 
            'cost',
            'sizes', 
            'phone_number', 
            'delivery_time',
            'support_duration', 
            'features', 
            'process_link',
            'service_id', 
            'payment_status', 
            'order_status', 
            'acceptance_status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = (
            'id',
            'shared_id',
            'user',
            'created_at',
            'updated_at',
            'service_id'
        )

    def validate_features(self, value):
        """Validate and normalize the features field"""
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

    def validate_sizes(self, value):
        """Validate the sizes dictionary structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Sizes must be a dictionary.")
        
        expected_sizes = {'small', 'medium', 'large', 'extraLarge', 'doubleExtraLarge'}
        if not all(size in expected_sizes for size in value.keys()):
            raise serializers.ValidationError("Invalid size keys provided.")
        
        if not all(isinstance(count, int) for count in value.values()):
            raise serializers.ValidationError("Size quantities must be integers.")
        
        return value

    def validate_phone_number(self, value):
        """Validate phone number format"""
        if not value:
            return value
            
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if not (6 <= len(value) <= 15):
            raise serializers.ValidationError("Phone number length must be between 6 and 15 digits.")
        return value
        
    def create(self, validated_data):
        """Create a new service instance"""
        # Set user from request context
        if self.context and 'request' in self.context:
            validated_data['user'] = self.context['request'].user
        
        # Generate service_id if not provided
        if 'service_id' not in validated_data or not validated_data['service_id']:
            validated_data['service_id'] = f"svc-{str(uuid.uuid4())[:8]}"
        
        return super().create(validated_data)