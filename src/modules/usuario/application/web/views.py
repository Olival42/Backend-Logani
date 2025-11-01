from rest_framework.views import APIView

from modules.usuario.application.web.serializers import (
    UserCreateSerializer,
    LoginSerializer,
)
from modules.usuario.domain.services import UserService
from modules.usuario.adapters.persistence.user_repository_django import UserRepository
from modules.usuario.adapters.persistence.blacklist_repository_django import BlacklistRepository
from api_pagamento_frete.utils import ErrorResponse, SuccessResponse

user_repository = UserRepository()
blacklist_repository = BlacklistRepository()
user_service = UserService(user_repository, blacklist_repository)

class RegisterView(APIView):
    def post(self, request):
        serializer = UserCreateSerializer(
            data=request.data,
            context={"user_service": user_service}
        )
        if serializer.is_valid():
            user_data = serializer.save()
            return SuccessResponse.created(
                data=user_data,
                message="Usuário criado com sucesso"
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