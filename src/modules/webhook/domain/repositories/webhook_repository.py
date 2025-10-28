from abc import ABC, abstractmethod
from typing import List, Optional
from modules.webhook.domain.entities.webhook_entity import Webhook


class IWebhookRepository(ABC):
    """Interface para repositório de Webhooks"""
    
    @abstractmethod
    def save(self, webhook: Webhook) -> Webhook:
        """Salva um webhook"""
        pass
    
    @abstractmethod
    def get_by_id(self, webhook_id: str) -> Optional[Webhook]:
        """Busca um webhook por ID"""
        pass
    
    @abstractmethod
    def get_by_asaas_id(self, asaas_id: str) -> Optional[Webhook]:
        """Busca um webhook por ID do ASAAS"""
        pass
    
    @abstractmethod
    def list_all(self) -> List[Webhook]:
        """Lista todos os webhooks"""
        pass
    
    @abstractmethod
    def update(self, webhook: Webhook) -> Webhook:
        """Atualiza um webhook"""
        pass
    
    @abstractmethod
    def delete(self, webhook_id: str) -> bool:
        """Remove um webhook"""
        pass
    
    @abstractmethod
    def get_active_webhooks(self) -> List[Webhook]:
        """Busca todos os webhooks ativos"""
        pass

