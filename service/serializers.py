from rest_framework import serializers
from .models import Service

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'user', 'title', 'description', 'cost', 'delivery_time', 'support_duration', 'features', 'process_link', 'service_id', 'payment_status', 'order_status']

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
