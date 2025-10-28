from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

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


class WebhookCreateView(APIView):
    """
    View para criar novos webhooks
    """
    
    def post(self, request):
        """Cria um novo webhook no ASAAS"""
        
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"detail": "Token não informado"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validação dos dados
        serializer = CreateWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )

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
            
            return Response(
                {
                    "message": "Webhook criado com sucesso",
                    "data": result
                },
                status=status.HTTP_201_CREATED
            )
            
        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Erro interno do servidor: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WebhookListView(APIView):
    """View para listar webhooks"""
    
    def get(self, request):
        """Lista todos os webhooks"""
        
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"detail": "Token não informado"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

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
            
            return Response(
                {
                    "message": f"Encontrados {len(webhooks)} webhooks",
                    "data": serializer.data,
                    "count": len(webhooks)
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": f"Erro interno do servidor: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WebhookDetailView(APIView):
    """View para detalhes de um webhook"""
    
    def get(self, request, webhook_id):
        """Consulta detalhes de um webhook"""
        
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"detail": "Token não informado"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Busca o webhook
        webhook_service = WebhookService(WebhookRepository())
        try:
            webhook = webhook_service.get_webhook(webhook_id)
            
            if not webhook:
                return Response(
                    {"error": "Webhook não encontrado"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
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
            
            return Response(
                {
                    "message": "Webhook encontrado",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": f"Erro interno do servidor: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WebhookUpdateView(APIView):
    """View para atualizar webhooks"""
    
    def put(self, request, webhook_id):
        """Atualiza um webhook"""
        
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"detail": "Token não informado"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validação dos dados
        serializer = UpdateWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )

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
            
            return Response(
                {
                    "message": "Webhook atualizado com sucesso",
                    "data": result
                },
                status=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Erro interno do servidor: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WebhookDeleteView(APIView):
    """View para remover webhooks"""
    
    def delete(self, request, webhook_id):
        """Remove um webhook"""
        
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"detail": "Token não informado"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Remoção do webhook
        webhook_service = WebhookService(WebhookRepository())
        try:
            result = webhook_service.delete_webhook(webhook_id)
            
            return Response(
                {
                    "message": "Webhook removido com sucesso",
                    "data": result
                },
                status=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Erro interno do servidor: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

