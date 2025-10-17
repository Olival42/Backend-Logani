from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from modules.cliente.application.web.serializers import CreateClientSerializer, UpdateClientSerializer
from modules.cliente.domain.services import ClientService
from modules.cliente.adapters.persistence.client_repository_django import ClientRepository
from modules.usuario.domain.services import UserService
from modules.usuario.adapters.persistence.user_repository_django import UserRepository
from modules.usuario.adapters.persistence.blacklist_repository_django import BlacklistRepository

class ClientCreateView(APIView):
    def post(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response({"detail": "Token não informado"}, status=status.HTTP_401_UNAUTHORIZED)

        token = auth_header.split(" ")[1]

        user_service = UserService(UserRepository(), BlacklistRepository())
        try:
            payload = user_service.authenticate(token)
            user_id = payload["user_id"]
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = CreateClientSerializer(data=request.data)
        if serializer.is_valid():
            repository = ClientRepository()
            service = ClientService(client_repository=repository)
            try:
                client_entity = service.create_client(serializer.validated_data, user_id=user_id)
                return Response({"id": client_entity.id}, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ClientDetailView(APIView):
    def get(self, request, client_id):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response({"detail": "Token não informado"}, status=status.HTTP_401_UNAUTHORIZED)

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())

        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        repository = ClientRepository()
        service = ClientService(client_repository=repository)

        try:
            client_data = service.get_client_by_id(client_id)
            return Response(client_data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
class ClientUpdateView(APIView):
    def patch(self, request, client_id):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response({"detail": "Token não informado"}, status=status.HTTP_401_UNAUTHORIZED)

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())

        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = UpdateClientSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        repository = ClientRepository()
        service = ClientService(client_repository=repository)

        try:
            updated_client = service.update_client(client_id, serializer.validated_data)
            return Response(
                {
                    "id": updated_client.id, 
                    "message": {
                        "detail": "Cliente atualizado com sucesso"
                    }
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
