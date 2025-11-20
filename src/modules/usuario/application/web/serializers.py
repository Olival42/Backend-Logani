from rest_framework import serializers
from django.db import DatabaseError, IntegrityError
from modules.usuario.domain.services import UserService
from modules.usuario.domain.entities import User

class UserCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=True, 
        allow_blank=False, 
        max_length=255,
        error_messages={
            "required": "O campo nome é obrigatório.",
            "blank": "O campo nome é obrigatório."
        }
    )
    email = serializers.EmailField(
        required=True, 
        allow_blank=False,
        error_messages={
            "required": "O campo email é obrigatório.",
            "blank": "O campo email é obrigatório.",
            "invalid": "Email inválido."
        }
    )
    password = serializers.CharField(
        required=True, 
        allow_blank=False, 
        write_only=True,
        error_messages={
            "required": "O campo senha é obrigatório.",
            "blank": "O campo senha é obrigatório."
        }
    )
    
    def validate_email(self, value):
        """Valida o formato do email usando a validação da entidade User"""
        try:
            return User.validate_email(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def validate_password(self, value):
        """Valida a senha usando a validação da entidade User"""
        try:
            return User.validate_password(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

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
        except (DatabaseError, IntegrityError) as e:
            # Captura erros de banco de dados (constraints, transações, etc)
            raise serializers.ValidationError({
                "error": {
                    "detail": f"Erro ao salvar no banco de dados: {str(e)}"
                }
            })
        except Exception as e:
            # Captura qualquer outro erro não esperado
            raise serializers.ValidationError({
                "error": {
                    "detail": f"Erro inesperado ao criar usuário: {str(e)}"
                }
            })
            
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True, 
        allow_blank=False,
        error_messages={
            "required": "O campo email é obrigatório.",
            "blank": "O campo email é obrigatório.",
            "invalid": "Email inválido."
        }
    )
    password = serializers.CharField(
        required=True,
        allow_blank=False,
        write_only=True,
        error_messages={
            "required": "O campo senha é obrigatório.",
            "blank": "O campo senha é obrigatório."
        }
    )
    
    def validate_email(self, value):
        """Valida o formato do email usando a validação da entidade User"""
        try:
            return User.validate_email(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

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

class UserUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=255,
        error_messages={
            "blank": "O campo nome não pode ser vazio.",
            "max_length": "O campo nome não pode ter mais de 255 caracteres."
        }
    )
    password = serializers.CharField(
        required=False,
        allow_blank=False,
        write_only=True,
        error_messages={
            "blank": "O campo senha não pode ser vazio."
        }
    )
    
    def validate_password(self, value):
        """Valida a senha usando a validação da entidade User"""
        try:
            return User.validate_password(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def validate(self, data):
        """Valida que pelo menos um campo foi fornecido para atualização"""
        if not any(key in data for key in ['name', 'password']):
            raise serializers.ValidationError({
                "error": {
                    "detail": "É necessário fornecer pelo menos um campo (name ou password) para atualização."
                }
            })
        return data
    
    def update(self, user_id: int, validated_data):
        """Atualiza o usuário com os dados validados"""
        user_service: UserService = self.context["user_service"]
        try:
            return user_service.update_user(
                user_id=user_id,
                name=validated_data.get("name"),
                password=validated_data.get("password")
            )
        except ValueError as e:
            raise serializers.ValidationError({
                "error": {
                    "detail": str(e)
                }
            })
        except (DatabaseError, IntegrityError) as e:
            raise serializers.ValidationError({
                "error": {
                    "detail": f"Erro ao salvar no banco de dados: {str(e)}"
                }
            })
        except Exception as e:
            raise serializers.ValidationError({
                "error": {
                    "detail": f"Erro inesperado ao atualizar usuário: {str(e)}"
                }
            })

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "O campo email é obrigatório.",
            "blank": "O campo email é obrigatório.",
            "invalid": "Email inválido."
        }
    )
    
    def validate_email(self, value):
        """Valida o formato do email usando a validação da entidade User"""
        try:
            return User.validate_email(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "O campo token é obrigatório.",
            "blank": "O campo token é obrigatório."
        }
    )
    password = serializers.CharField(
        required=True,
        allow_blank=False,
        write_only=True,
        error_messages={
            "required": "O campo senha é obrigatório.",
            "blank": "O campo senha é obrigatório."
        }
    )
    
    def validate_password(self, value):
        """Valida a senha usando a validação da entidade User"""
        try:
            return User.validate_password(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))