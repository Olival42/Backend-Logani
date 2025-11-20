from rest_framework.views import APIView
from django.db import DatabaseError, IntegrityError

from modules.usuario.application.web.serializers import (
    UserCreateSerializer,
    LoginSerializer,
    UserUpdateSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)
from modules.usuario.domain.services import UserService
from modules.usuario.adapters.persistence.user_repository_django import UserRepository
from modules.usuario.adapters.persistence.blacklist_repository_django import BlacklistRepository
from modules.usuario.adapters.persistence.password_reset_repository_django import PasswordResetRepository
from modules.email.domain.services.email_service import EmailService
from api_pagamento_frete.utils import ErrorResponse, SuccessResponse
from django.db import DatabaseError, IntegrityError

user_repository = UserRepository()
blacklist_repository = BlacklistRepository()
password_reset_repository = PasswordResetRepository()
user_service = UserService(user_repository, blacklist_repository, password_reset_repository)
email_service = EmailService()

class RegisterView(APIView):
    def post(self, request):
        serializer = UserCreateSerializer(
            data=request.data,
            context={"user_service": user_service}
        )
        if serializer.is_valid():
            try:
                user_data = serializer.save()
                return SuccessResponse.created(
                    data=user_data,
                    message="Usuário criado com sucesso"
                )
            except (DatabaseError, IntegrityError) as e:
                # Erro de banco de dados não capturado pelo serializer
                return ErrorResponse.internal_server_error(
                    "Erro ao salvar usuário no banco de dados",
                    details=str(e)
                )
            except Exception as e:
                # Qualquer outro erro inesperado
                return ErrorResponse.internal_server_error(
                    "Erro inesperado ao criar usuário",
                    details=str(e)
                )
        
        return ErrorResponse.validation_error(serializer.errors)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"user_service": user_service})
        if serializer.is_valid():
            result = serializer.validated_data
            return SuccessResponse.ok(data=result, message="Login realizado com sucesso")
        return ErrorResponse.validation_error(serializer.errors)
    
class LogoutView(APIView):
    def post(self, request):
        auth_header = request.headers.get("Authorization")
        refresh_token = request.data.get("refresh")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.bad_request("Access token não informado")
        
        if not refresh_token:
            return ErrorResponse.bad_request("Refresh token obrigatório")

        access_token = auth_header.split()[1]

        result = user_service.logout(access_token, refresh_token)

        if "Logout realizado" in result["detail"]:
            return SuccessResponse.ok(data=result, message="Logout realizado com sucesso")
        return ErrorResponse.bad_request(result.get("detail", "Erro ao realizar logout"))
    
class RefreshTokenView(APIView): 
    def post(self, request): 
        refresh_token = request.data.get("refresh") 
        if not refresh_token: 
            return ErrorResponse.bad_request("Refresh token não informado")
        try: 
            result = user_service.refresh_access_token(refresh_token) 
            return SuccessResponse.ok(data=result, message="Token atualizado com sucesso")
        except ValueError as e: 
            return ErrorResponse.unauthorized(str(e))

class UpdateUserView(APIView):
    """View para atualizar informações do usuário autenticado"""
    
    def put(self, request):
        """Atualiza informações do usuário autenticado"""
        
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token não informado")
        
        token = auth_header.split(" ")[1]
        
        try:
            payload = user_service.authenticate(token)
            user_id = payload.get('user_id')
        except ValueError as e:
            return ErrorResponse.unauthorized(str(e))
        
        # Validação dos dados
        serializer = UserUpdateSerializer(
            data=request.data,
            context={"user_service": user_service}
        )
        
        if serializer.is_valid():
            try:
                user_data = serializer.update(user_id, serializer.validated_data)
                return SuccessResponse.ok(
                    data=user_data,
                    message="Usuário atualizado com sucesso"
                )
            except (DatabaseError, IntegrityError) as e:
                return ErrorResponse.internal_server_error(
                    "Erro ao salvar usuário no banco de dados",
                    details=str(e)
                )
            except Exception as e:
                return ErrorResponse.internal_server_error(
                    "Erro inesperado ao atualizar usuário",
                    details=str(e)
                )
        
        return ErrorResponse.validation_error(serializer.errors)
    
    def patch(self, request):
        """Atualiza informações do usuário autenticado (método PATCH)"""
        return self.put(request)

class ForgotPasswordView(APIView):
    """View para solicitar reset de senha"""
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            try:
                email = serializer.validated_data['email']
                result = user_service.request_password_reset(email)
                
                # Se o resultado contém token, significa que o usuário existe e o email deve ser enviado
                if 'token' in result:
                    # Envia o email de reset
                    email_sent = email_service.send_password_reset_email(
                        user_email=result['user_email'],
                        user_name=result['user_name'],
                        reset_token=result['token']
                    )
                    
                    if not email_sent:
                        # Log do erro mas retorna sucesso mesmo assim (para não revelar informações)
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Erro ao enviar email de reset para {result['user_email']}")
                
                # Sempre retorna a mesma mensagem genérica (por segurança)
                return SuccessResponse.ok(
                    data={"message": result['message']},
                    message="Se o email estiver cadastrado, você receberá um link para resetar sua senha"
                )
            except Exception as e:
                # Retorna sucesso mesmo em caso de erro (para não revelar informações)
                return SuccessResponse.ok(
                    data={"message": "Se o email estiver cadastrado, você receberá um link para resetar sua senha"},
                    message="Se o email estiver cadastrado, você receberá um link para resetar sua senha"
                )
        
        return ErrorResponse.validation_error(serializer.errors)

class ResetPasswordView(APIView):
    """View para resetar senha usando token"""
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            try:
                token = serializer.validated_data['token']
                new_password = serializer.validated_data['password']
                
                result = user_service.reset_password(token, new_password)
                
                return SuccessResponse.ok(
                    data=result,
                    message="Senha alterada com sucesso"
                )
            except ValueError as e:
                return ErrorResponse.bad_request(str(e))
            except Exception as e:
                return ErrorResponse.internal_server_error(
                    "Erro ao resetar senha",
                    details=str(e)
                )
        
        return ErrorResponse.validation_error(serializer.errors)