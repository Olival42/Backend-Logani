from rest_framework.views import APIView

from modules.webhook.application.web.serializers import (
    CreateWebhookSerializer,
    UpdateWebhookSerializer,
    WebhookResponseSerializer,
    WebhookListSerializer
)
from modules.webhook.domain.services.webhook_service import WebhookService
from modules.webhook.adapters.persistence.webhook_repository_django import WebhookRepository
from modules.usuario.domain.services import UserService
from modules.usuario.adapters.persistence.user_repository_django import UserRepository
from modules.usuario.adapters.persistence.blacklist_repository_django import BlacklistRepository
from api_pagamento_frete.utils import ErrorResponse, SuccessResponse


class WebhookCreateView(APIView):
    """
    View para criar novos webhooks
    """
    
    def post(self, request):
        """Cria um novo webhook no ASAAS"""
        
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
        serializer = CreateWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse.validation_error(serializer.errors)

        # Criação do webhook
        webhook_service = WebhookService(WebhookRepository())
        try:
            result = webhook_service.create_webhook(
                url=serializer.validated_data['url'],
                events=serializer.validated_data['events'],
                email=serializer.validated_data.get('email'),
                api_version=serializer.validated_data.get('api_version', 'v3'),
                auth_token=serializer.validated_data.get('auth_token'),
                enabled=serializer.validated_data.get('enabled', True)
            )
            
            return SuccessResponse.created(
                data=result,
                message="Webhook criado com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class WebhookListView(APIView):
    """View para listar webhooks"""
    
    def get(self, request):
        """Lista todos os webhooks"""
        
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

        # Lista webhooks
        webhook_service = WebhookService(WebhookRepository())
        try:
            webhooks = webhook_service.list_webhooks()
            
            # Serializa os dados
            serializer = WebhookListSerializer([
                {
                    'id': webhook.id,
                    'url': webhook.url,
                    'email': webhook.email,
                    'events': webhook.events,
                    'status': webhook.status,
                    'enabled': webhook.enabled,
                    'created_at': webhook.created_at,
                }
                for webhook in webhooks
            ], many=True)
            
            return SuccessResponse.ok(
                data={
                    "webhooks": serializer.data,
                    "count": len(webhooks)
                },
                message=f"Encontrados {len(webhooks)} webhooks"
            )
            
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class WebhookDetailView(APIView):
    """View para detalhes de um webhook"""
    
    def get(self, request, webhook_id):
        """Consulta detalhes de um webhook"""
        
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

        # Busca o webhook
        webhook_service = WebhookService(WebhookRepository())
        try:
            webhook = webhook_service.get_webhook(webhook_id)
            
            if not webhook:
                return ErrorResponse.not_found("Webhook não encontrado")
            
            # Serializa os dados
            serializer = WebhookResponseSerializer({
                'local_id': webhook.id,
                'asaas_id': webhook.asaas_webhook_id,
                'url': webhook.url,
                'email': webhook.email,
                'events': webhook.events,
                'status': webhook.status,
                'enabled': webhook.enabled,
                'api_version': webhook.api_version,
                'created_at': webhook.created_at,
                'updated_at': webhook.updated_at,
            })
            
            return SuccessResponse.ok(
                data=serializer.data,
                message="Webhook encontrado"
            )
            
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class WebhookUpdateView(APIView):
    """View para atualizar webhooks"""
    
    def put(self, request, webhook_id):
        """Atualiza um webhook"""
        
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
        serializer = UpdateWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse.validation_error(serializer.errors)

        # Atualização do webhook
        webhook_service = WebhookService(WebhookRepository())
        try:
            result = webhook_service.update_webhook(
                webhook_id=webhook_id,
                url=serializer.validated_data.get('url'),
                events=serializer.validated_data.get('events'),
                email=serializer.validated_data.get('email'),
                enabled=serializer.validated_data.get('enabled'),
                auth_token=serializer.validated_data.get('auth_token')
            )
            
            return SuccessResponse.ok(
                data=result,
                message="Webhook atualizado com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class WebhookDeleteView(APIView):
    """View para remover webhooks"""
    
    def delete(self, request, webhook_id):
        """Remove um webhook"""
        
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

        # Remoção do webhook
        webhook_service = WebhookService(WebhookRepository())
        try:
            result = webhook_service.delete_webhook(webhook_id)
            
            return SuccessResponse.ok(
                data=result,
                message="Webhook removido com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )

