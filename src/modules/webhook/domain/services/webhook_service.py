from typing import Dict, Any, List, Optional
from modules.webhook.domain.entities.webhook_entity import Webhook
from modules.webhook.domain.repositories.webhook_repository import IWebhookRepository
from modules.webhook.adapters.external.asaas_webhook_client import AsaasWebhookClient


class WebhookService:
    """
    Serviço de domínio para gerenciamento de webhooks
    """
    
    def __init__(self, webhook_repository: IWebhookRepository):
        self.webhook_repository = webhook_repository
        self.asaas_client = AsaasWebhookClient()
    
    def create_webhook(
        self,
        url: str,
        events: List[str],
        email: Optional[str] = None,
        api_version: str = 'v3',
        auth_token: Optional[str] = None,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Cria um novo webhook
        
        Args:
            url: URL do webhook
            events: Lista de eventos
            email: Email para notificações
            api_version: Versão da API
            auth_token: Token de autenticação
            enabled: Webhook habilitado
        
        Returns:
            Dict com informações do webhook criado
        """
        try:
            # Cria a entidade webhook
            webhook = Webhook(
                id=None,  # Será gerado pelo repositório
                url=url,
                email=email,
                enabled=enabled,
                status='ACTIVE',
                events=events,
                api_version=api_version,
                auth_token=auth_token
            )
            
            # Cria no ASAAS
            asaas_response = self.asaas_client.create_webhook(
                url=url,
                events=events,
                email=email,
                api_version=api_version,
                auth_token=auth_token,
                enabled=enabled
            )
            
            if 'id' not in asaas_response:
                raise ValueError("ASAAS não retornou ID do webhook criado")
            
            # Atualiza a entidade com os dados do ASAAS
            webhook.asaas_webhook_id = asaas_response['id']
            
            # Salva no repositório local
            saved_webhook = self.webhook_repository.save(webhook)
            
            return {
                'local_id': str(saved_webhook.id),
                'asaas_id': saved_webhook.asaas_webhook_id,
                'url': saved_webhook.url,
                'events': saved_webhook.events,
                'status': saved_webhook.status,
                'enabled': saved_webhook.enabled,
                'asaas_response': asaas_response
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao criar webhook: {str(e)}")
    
    def update_webhook(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        email: Optional[str] = None,
        enabled: Optional[bool] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Atualiza um webhook existente
        
        Args:
            webhook_id: ID do webhook local
            url: Nova URL
            events: Novos eventos
            email: Novo email
            enabled: Novo status
            auth_token: Novo token
        
        Returns:
            Dict com informações do webhook atualizado
        """
        try:
            # Busca o webhook local
            webhook = self.webhook_repository.get_by_id(webhook_id)
            if not webhook:
                raise ValueError("Webhook não encontrado")
            
            if not webhook.asaas_webhook_id:
                raise ValueError("Webhook não está sincronizado com o ASAAS")
            
            # Atualiza os campos se fornecidos
            if url:
                webhook.url = url
            if events is not None:
                webhook.events = events
            if email is not None:
                webhook.email = email
            if enabled is not None:
                webhook.enabled = enabled
            if auth_token is not None:
                webhook.auth_token = auth_token
            
            # Atualiza no ASAAS
            asaas_response = self.asaas_client.update_webhook(
                webhook_id=webhook.asaas_webhook_id,
                url=url,
                events=events,
                email=email,
                enabled=enabled,
                auth_token=auth_token
            )
            
            # Atualiza localmente
            updated_webhook = self.webhook_repository.update(webhook)
            
            return {
                'local_id': str(updated_webhook.id),
                'asaas_id': updated_webhook.asaas_webhook_id,
                'url': updated_webhook.url,
                'events': updated_webhook.events,
                'status': updated_webhook.status,
                'enabled': updated_webhook.enabled,
                'asaas_response': asaas_response
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao atualizar webhook: {str(e)}")
    
    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Busca um webhook por ID"""
        return self.webhook_repository.get_by_id(webhook_id)
    
    def list_webhooks(self) -> List[Webhook]:
        """Lista todos os webhooks"""
        return self.webhook_repository.list_all()
    
    def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Remove um webhook
        
        Args:
            webhook_id: ID do webhook local
        
        Returns:
            Dict com resultado da remoção
        """
        try:
            # Busca o webhook local
            webhook = self.webhook_repository.get_by_id(webhook_id)
            if not webhook:
                raise ValueError("Webhook não encontrado")
            
            # Remove do ASAAS se tiver ID
            asaas_response = None
            if webhook.asaas_webhook_id:
                try:
                    asaas_response = self.asaas_client.delete_webhook(webhook.asaas_webhook_id)
                except Exception as e:
                    # Log do erro mas continua a remoção local
                    pass
            
            # Remove localmente
            deleted = self.webhook_repository.delete(webhook_id)
            
            return {
                'local_id': webhook_id,
                'deleted': deleted,
                'asaas_response': asaas_response
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao remover webhook: {str(e)}")
    
    def sync_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Sincroniza um webhook com o ASAAS
        
        Args:
            webhook_id: ID do webhook local
        
        Returns:
            Dict com informações da sincronização
        """
        try:
            # Busca o webhook local
            webhook = self.webhook_repository.get_by_id(webhook_id)
            if not webhook:
                raise ValueError("Webhook não encontrado")
            
            if not webhook.asaas_webhook_id:
                raise ValueError("Webhook não está sincronizado com o ASAAS")
            
            # Busca dados atualizados no ASAAS
            asaas_response = self.asaas_client.get_webhook(webhook.asaas_webhook_id)
            
            # Atualiza localmente com dados do ASAAS
            if 'url' in asaas_response:
                webhook.url = asaas_response.get('url')
            if 'enabled' in asaas_response:
                webhook.enabled = asaas_response.get('enabled')
            if 'events' in asaas_response:
                webhook.events = asaas_response.get('events')
            
            updated_webhook = self.webhook_repository.update(webhook)
            
            return {
                'local_id': str(updated_webhook.id),
                'asaas_id': updated_webhook.asaas_webhook_id,
                'url': updated_webhook.url,
                'events': updated_webhook.events,
                'status': updated_webhook.status,
                'enabled': updated_webhook.enabled,
                'asaas_data': asaas_response
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao sincronizar webhook: {str(e)}")
    
    def get_active_webhooks(self) -> List[Webhook]:
        """Retorna todos os webhooks ativos"""
        return self.webhook_repository.get_active_webhooks()

