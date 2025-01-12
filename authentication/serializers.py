
    
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from service.models import Service

class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    user_type = serializers.ChoiceField(choices=User.Types.choices, required=False, default=User.Types.CLIENT)  # Make user_type optional with default

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'user_type']  # Include user_type in case the frontend provides it
    
    def create(self, validated_data):
        user_type = validated_data.get('user_type', User.Types.CLIENT)  # Default to CLIENT if not provided
        validated_data['user_type'] = user_type
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            user_type=user_type
        )
        return user


class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("Invalid credentials")

        if not user.check_password(password):
            raise ValidationError("Invalid credentials")

        attrs['user'] = user
        return attrs



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']