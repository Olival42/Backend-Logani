from rest_framework.views import APIView

from modules.cliente.application.web.asaas_serializers import (
    AsaasCreateClientSerializer,
    AsaasUpdateClientSerializer,
)
from modules.cliente.domain.services.asaas_client_service import AsaasClientService
from modules.cliente.domain.services.client_service import ClientService
from modules.cliente.adapters.persistence.client_repository_django import ClientRepository
from modules.usuario.domain.services import UserService
from modules.usuario.adapters.persistence.user_repository_django import UserRepository
from modules.usuario.adapters.persistence.blacklist_repository_django import BlacklistRepository
from api_pagamento_frete.utils import ErrorResponse, SuccessResponse


class AsaasClientCreateView(APIView):
    """
    View para criar clientes com integração ao Asaas
    """
    
    def post(self, request):
        """
        Cria um novo cliente local e sincroniza com o Asaas
        
        Body:
        {
            "name": "Nome do Cliente",
            "cpf": "12345678901",
            "phone": "11999999999",
            "mobile_phone": "11999999999",
            "email": "cliente@email.com",  // opcional
            "externalReference": "REF123",  // opcional
            "notificationDisabled": false,  // opcional
            "additionalEmails": ["email1@test.com", "email2@test.com"],  // opcional
            "address": {
                "address": "Rua das Flores",
                "number": "123",
                "postal_code": "01234567",
                "city": "São Paulo",
                "state": "SP",
                "province": "Centro",
                "complement": "Apto 45"
            }
        }
        """
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token não informado")

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            payload = user_service.authenticate(token)
            user_id = payload["user_id"]
        except ValueError as e:
            return ErrorResponse.unauthorized(str(e))

        # Validação dos dados
        serializer = AsaasCreateClientSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse.validation_error(serializer.errors)

        # Criação do cliente
        asaas_service = AsaasClientService()
        try:
            result = asaas_service.create_client_with_asaas(
                serializer.validated_data, 
                user_id
            )
            
            return SuccessResponse.created(
                data=result,
                message="Cliente criado com sucesso no Asaas e sincronizado no sistema local"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class AsaasClientUpdateView(APIView):
    """
    View para atualizar clientes com integração ao Asaas
    """
    
    def patch(self, request, client_id):
        """
        Atualiza um cliente local e sincroniza com o Asaas
        
        Body: (todos os campos são opcionais)
        {
            "name": "Novo Nome",
            "cpf": "98765432100",
            "phone": "11888888888",
            "mobile_phone": "11888888888",
            "email": "novo@email.com",
            "externalReference": "REF456",
            "notificationDisabled": true,
            "additionalEmails": ["novo@test.com"],
            "address": {
                "address": "Nova Rua",
                "number": "456",
                "postal_code": "76543210",
                "city": "Rio de Janeiro",
                "state": "RJ",
                "province": "Copacabana",
                "complement": "Casa 2"
            }
        }
        """
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token não informado")

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return ErrorResponse.unauthorized(str(e))

        # Validação dos dados
        serializer = AsaasUpdateClientSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return ErrorResponse.validation_error(serializer.errors)

        # Atualização do cliente
        asaas_service = AsaasClientService()
        try:
            result = asaas_service.update_client_with_asaas(
                client_id, 
                serializer.validated_data
            )
            
            return SuccessResponse.ok(
                data=result,
                message="Cliente atualizado com sucesso no Asaas e sincronizado no sistema local"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class AsaasClientSyncView(APIView):
    """
    View para sincronizar clientes existentes com o Asaas
    """
    
    def post(self, request, client_id):
        """
        Sincroniza um cliente local existente com o Asaas
        """
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token não informado")

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return ErrorResponse.unauthorized(str(e))

        # Sincronização
        asaas_service = AsaasClientService()
        try:
            result = asaas_service.sync_client_to_asaas(client_id)
            
            return SuccessResponse.ok(
                data=result,
                message=f"Cliente {result['action']} no Asaas com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class AsaasClientDetailView(APIView):
    """
    View para consultar dados de clientes diretamente do Asaas usando ID local
    """
    
    def get(self, request, client_id):
        """
        Consulta dados de um cliente diretamente do Asaas usando o ID local do cliente
        
        Args:
            client_id: ID do cliente no sistema local (UUID)
            
        Returns:
            Dados do cliente do Asaas, incluindo:
            - local_id: ID do cliente no sistema local
            - asaas_id: ID do cliente no Asaas
            - asaas_data: Dados completos do cliente no Asaas
        """
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token não informado")

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return ErrorResponse.unauthorized(str(e))

        # Consulta no Asaas usando ID local
        asaas_service = AsaasClientService()
        try:
            result = asaas_service.get_client_from_asaas_by_local_id(client_id)
            
            return SuccessResponse.ok(
                data=result,
                message="Dados do cliente recuperados do Asaas"
            )
            
        except ValueError as e:
            return ErrorResponse.not_found(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class ClientByBearerTokenView(APIView):
    """
    View para buscar informações do cliente e usuário associados através do Bearer Token
    """
    
    def get(self, request):
        """
        Retorna informações do usuário e cliente associados ao token Bearer
        
        Headers:
            Authorization: Bearer <token>
            
        Returns:
            Dicionário contendo informações do usuário e cliente:
            {
                "user": {
                    "id": int,
                    "name": str,
                    "email": str,
                    "active": bool,
                    "registration_date": str (ISO format)
                },
                "client": {
                    "id": str (UUID),
                    "name": str,
                    "cpf": str,
                    "phone": str,
                    "mobile_phone": str,
                    "registration_date": str (ISO format),
                    "active": bool,
                    "asaas_id": str,
                    "address": {
                        "address": str,
                        "number": str,
                        "postal_code": str,
                        "city": str,
                        "state": str,
                        "complement": str,
                        "province": str
                    }
                }
            }
        """
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token não informado")

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            payload = user_service.authenticate(token)
            user_id = payload["user_id"]
        except ValueError as e:
            return ErrorResponse.unauthorized(str(e))

        # Busca o cliente pelo user_id
        client_service = ClientService(ClientRepository())
        try:
            result = client_service.get_client_by_bearer_token(user_id)
            
            return SuccessResponse.ok(data=result)
            
        except ValueError as e:
            return ErrorResponse.not_found(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )
