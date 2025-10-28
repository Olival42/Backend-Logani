from typing import List, Optional
from uuid import uuid4
from modules.webhook.domain.entities.webhook_entity import Webhook
from modules.webhook.domain.repositories.webhook_repository import IWebhookRepository
from modules.webhook.adapters.persistence.models import Webhook as WebhookModel


class WebhookRepository(IWebhookRepository):
    """Implementação do repositório de webhooks usando Django ORM"""
    
    def save(self, webhook: Webhook) -> Webhook:
        """Salva um webhook"""
        try:
            # Cria ou atualiza o modelo
            webhook_model, created = WebhookModel.objects.update_or_create(
                id=webhook.id or str(uuid4()),
                defaults={
                    'url': webhook.url,
                    'email': webhook.email,
                    'enabled': webhook.enabled,
                    'status': webhook.status,
                    'events': webhook.events,
                    'api_version': webhook.api_version,
                    'auth_token': webhook.auth_token,
                    'asaas_webhook_id': webhook.asaas_webhook_id,
                }
            )
            
            webhook.id = str(webhook_model.id)
            return webhook
            
        except Exception as e:
            raise ValueError(f"Erro ao salvar webhook: {str(e)}")
    
    def get_by_id(self, webhook_id: str) -> Optional[Webhook]:
        """Busca um webhook por ID"""
        try:
            webhook_model = WebhookModel.objects.get(id=webhook_id)
            return self._model_to_entity(webhook_model)
        except WebhookModel.DoesNotExist:
            return None
    
    def get_by_asaas_id(self, asaas_id: str) -> Optional[Webhook]:
        """Busca um webhook por ID do ASAAS"""
        try:
            webhook_model = WebhookModel.objects.get(asaas_webhook_id=asaas_id)
            return self._model_to_entity(webhook_model)
        except WebhookModel.DoesNotExist:
            return None
    
    def list_all(self) -> List[Webhook]:
        """Lista todos os webhooks"""
        webhook_models = WebhookModel.objects.all().order_by('-created_at')
        return [self._model_to_entity(model) for model in webhook_models]
    
    def update(self, webhook: Webhook) -> Webhook:
        """Atualiza um webhook"""
        if not webhook.id:
            raise ValueError("Webhook ID é obrigatório para atualização")
        
        try:
            webhook_model = WebhookModel.objects.get(id=webhook.id)
            
            webhook_model.url = webhook.url
            webhook_model.email = webhook.email
            webhook_model.enabled = webhook.enabled
            webhook_model.status = webhook.status
            webhook_model.events = webhook.events
            webhook_model.api_version = webhook.api_version
            webhook_model.auth_token = webhook.auth_token
            webhook_model.asaas_webhook_id = webhook.asaas_webhook_id
            
            webhook_model.save()
            
            return webhook
            
        except WebhookModel.DoesNotExist:
            raise ValueError("Webhook não encontrado para atualização")
    
    def delete(self, webhook_id: str) -> bool:
        """Remove um webhook"""
        try:
            webhook_model = WebhookModel.objects.get(id=webhook_id)
            webhook_model.delete()
            return True
        except WebhookModel.DoesNotExist:
            return False
    
    def get_active_webhooks(self) -> List[Webhook]:
        """Busca todos os webhooks ativos"""
        webhook_models = WebhookModel.objects.filter(enabled=True, status='ACTIVE')
        return [self._model_to_entity(model) for model in webhook_models]
    
    def _model_to_entity(self, model: WebhookModel) -> Webhook:
        """Converte modelo Django para entidade de domínio"""
        return Webhook(
            id=str(model.id),
            url=model.url,
            email=model.email,
            enabled=model.enabled,
            status=model.status,
            events=model.events,
            api_version=model.api_version,
            auth_token=model.auth_token,
            created_at=model.created_at,
            updated_at=model.updated_at,
            asaas_webhook_id=model.asaas_webhook_id
        )

