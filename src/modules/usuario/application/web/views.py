from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from modules.usuario.application.web.serializers import (
    UserCreateSerializer,
    LoginSerializer,
)
from modules.usuario.domain.services import UserService
from modules.usuario.adapters.persistence.user_repository_django import UserRepository
from modules.usuario.adapters.persistence.blacklist_repository_django import BlacklistRepository

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

            return Response(user_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"user_service": user_service})
        if serializer.is_valid():
            result = serializer.validated_data
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LogoutView(APIView):
    def post(self, request):
        auth_header = request.headers.get("Authorization")
        refresh_token = request.data.get("refresh")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response({"detail": "Access token não informado"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not refresh_token:
            return Response({"detail": "Refresh token obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        access_token = auth_header.split()[1]

        result = user_service.logout(access_token, refresh_token)

        if "Logout realizado" in result["detail"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
class RefreshTokenView(APIView): 
    def post(self, request): 
        refresh_token = request.data.get("refresh") 
        if not refresh_token: 
            return Response({"detail": "Refresh token não informado"}, status=status.HTTP_400_BAD_REQUEST) 
        try: 
            result = user_service.refresh_access_token(refresh_token) 
            return Response(result, status=status.HTTP_200_OK) 
        except ValueError as e: 
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)