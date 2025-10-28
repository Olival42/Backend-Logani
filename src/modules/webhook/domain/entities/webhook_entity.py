from typing import List, Optional
from datetime import datetime
from decimal import Decimal


class Webhook:
    """
    Entidade de domínio para Webhook do ASAAS
    """
    
    def __init__(
        self,
        id: Optional[str] = None,
        url: str = None,
        email: Optional[str] = None,
        enabled: bool = True,
        status: str = 'ACTIVE',
        events: Optional[List[str]] = None,
        api_version: str = 'v3',
        auth_token: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        asaas_webhook_id: Optional[str] = None
    ):
        self.id = id
        self.url = url
        self.email = email
        self.enabled = enabled
        self.status = status
        self.events = events or []
        self.api_version = api_version
        self.auth_token = auth_token
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.asaas_webhook_id = asaas_webhook_id
    
    def is_active(self) -> bool:
        """Verifica se o webhook está ativo"""
        return self.enabled and self.status == 'ACTIVE'
    
    def deactivate(self):
        """Desativa o webhook"""
        self.enabled = False
        self.updated_at = datetime.now()
    
    def activate(self):
        """Ativa o webhook"""
        self.enabled = True
        self.status = 'ACTIVE'
        self.updated_at = datetime.now()
    
    def add_event(self, event: str):
        """Adiciona um evento à lista"""
        if event not in self.events:
            self.events.append(event)
            self.updated_at = datetime.now()
    
    def remove_event(self, event: str):
        """Remove um evento da lista"""
        if event in self.events:
            self.events.remove(event)
            self.updated_at = datetime.now()
    
    def has_event(self, event: str) -> bool:
        """Verifica se possui um evento específico"""
        return event in self.events
    
    def __repr__(self):
        return f"<Webhook {self.url} - {len(self.events)} events - {self.status}>"

