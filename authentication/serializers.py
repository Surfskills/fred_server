from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenVerifySerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import UntypedToken
from authentication.tokens import GigsHubRefreshToken
from tenancy.services import build_auth_claims

from .models import User


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    onboarding_intent = serializers.ChoiceField(
        choices=(
            ("hire", "Hire talent"),
            ("work", "Offer services"),
            ("both", "Both"),
        ),
        required=False,
        default="work",
        write_only=True,
    )

    user_type = serializers.ChoiceField(
        choices=User.Types.choices, 
        required=False, 
        default=User.Types.FREELANCER
    )

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'user_type', 'onboarding_intent', 'first_name', 'last_name']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
    

    
    def create(self, validated_data):
        # Work on a copy so serializer.validated_data keeps onboarding_intent
        # for post-save onboarding logic in the view.
        payload = dict(validated_data)
        payload.pop('onboarding_intent', None)
        user_type = payload.get('user_type', User.Types.FREELANCER)
        payload['user_type'] = user_type

        user = User.objects.create_user(
            email=payload['email'],
            password=payload['password'],
            user_type=user_type,
            first_name=payload.get('first_name', ''),
            last_name=payload.get('last_name', '')
        )

        return user


class CapabilityUpgradeSerializer(serializers.Serializer):
    """
    Self-service capability upgrades for the current account.
    Freelancer tier upgrades on GigsHub: Native reflects selective intake coordinated with implementing partners (e.g. niche craftsmanship).
    Dynamic and Demers: finish implementing partner certifications (WeDemo Africa) before claiming those tiers—GigsHub aligns policy only; partners run their own programmes.
    """

    capability = serializers.ChoiceField(
        choices=(
            ("client", "Client"),
            ("support", "Support"),
            ("admin", "Admin"),
            (
                "native",
                "Native — Partner-selective intake · rare niche skills (operators on GigsHub)",
            ),
            (
                "dynamic",
                "Dynamic — Implementing-partner certification on file · enterprise / big-tech (ex or current) + freelance",
            ),
            (
                "demer",
                "Demers — Partner certification prerequisite · technocrats (elite private practice)",
            ),
        )
    )


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
        
        if not user.is_active:
            raise ValidationError("User account is disabled")

        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    auth_context = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'is_staff', 'is_active', 'phone_number',
            'created_at', 'auth_context',
        ]
        read_only_fields = ['id', 'created_at', 'auth_context']

    def get_auth_context(self, obj):
        override = self.context.get('auth_context')
        if override is not None:
            return override
        if 'acting_organization_id' in self.context:
            acting = self.context.get('acting_organization_id')
            return build_auth_claims(obj, acting_organization_id=acting or None)
        return build_auth_claims(obj, acting_organization_id=None)


class CustomTokenVerifySerializer(TokenVerifySerializer):
    """
    Custom token verify serializer that provides better error messages
    """
    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except Exception as e:
            raise ValidationError({
                'token': ['Token is invalid or expired']
            })


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Refresh access token and preserve GigsHub claims (incl. acting_org_id on refresh).
    """
    def validate(self, attrs):
        try:
            decoded = UntypedToken(attrs['refresh'])
        except Exception:
            raise ValidationError({'refresh': ['Refresh token is invalid or expired']})

        acting = decoded.get('acting_org_id') or None
        if acting == '':
            acting = None
        user_id = decoded['user_id']

        try:
            data = super().validate(attrs)
        except Exception:
            raise ValidationError({'refresh': ['Refresh token is invalid or expired']})

        user = User.objects.get(pk=user_id)
        pair = GigsHubRefreshToken.for_user(user, acting_organization_id=acting)
        data['access'] = str(pair.access_token)
        if 'refresh' in data:
            data['refresh'] = str(pair)
        return data


class PasswordResetSerializer(serializers.Serializer):
    """
    Serializer for password reset requests
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            if not user.is_active:
                raise ValidationError("User account is disabled")
        except User.DoesNotExist:
            raise ValidationError("No user found with this email address")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation
    """
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)
  




class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user information
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number']
        
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing user password
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
 


    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise ValidationError("Old password is incorrect")
        return value