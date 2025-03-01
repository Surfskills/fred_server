from rest_framework import serializers
from .models import Service

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            'id', 'user', 'title', 'description', 'cost', 
            'sizes', 'phone_number', 'delivery_time', 
            'support_duration', 'features', 'process_link', 
            'service_id', 'payment_status', 'order_status', 'acceptance_status',
        ]

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

    # Validate `svg_image` to ensure it is a valid URL
    def validate_svg_image(self, value):
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("svg_image must be a valid URL. If you're using local files, configure the backend to handle file uploads.")
        return value

    # Ensure `category` is provided and valid
    def validate_category(self, value):
        if not value:
            raise serializers.ValidationError("Category is required.")
        return value

    # Validate sizes structure
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
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if not (6 <= len(value) <= 15):
            raise serializers.ValidationError("Phone number length must be between 6 and 15 digits.")
        return value
    
