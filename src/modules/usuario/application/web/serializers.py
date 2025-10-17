from rest_framework import serializers
from modules.usuario.domain.services import UserService

class UserCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    email = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def create(self, validated_data):
        user_service: UserService = self.context["user_service"]
        try:
            return user_service.create_user(
                name=validated_data["name"],
                email=validated_data["email"],
                password=validated_data["password"]
            )
        except ValueError as e:
            raise serializers.ValidationError({
                "error": {
                    "detail": str(e)
                }
            })
            
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user_service: UserService = self.context["user_service"]
        try:
            return user_service.login_user(
                email=data["email"],
                password=data["password"]
            )
        except ValueError as e:
            raise serializers.ValidationError({
                "error": {
                    "detail": str(e)
                }
            })