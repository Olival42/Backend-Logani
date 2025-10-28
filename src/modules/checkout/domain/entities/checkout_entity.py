from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from modules.cliente.domain.entities.client_entity import Client as ClientEntity


class Checkout:
    """
    Entidade de domínio para Checkout
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        value: Decimal,
        client: ClientEntity,
        installments: int = 1,
        description: Optional[str] = None,
        status: str = 'PENDING',
        asaas_id: Optional[str] = None,
        checkout_url: Optional[str] = None,
        success_url: Optional[str] = None,
        failure_url: Optional[str] = None,
        expires_url: Optional[str] = None,
        external_reference: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None
    ):
        self.id = id
        self.name = name
        self.value = value
        self.client = client
        self.installments = installments
        self.description = description
        self.status = status
        self.asaas_id = asaas_id
        self.checkout_url = checkout_url
        self.success_url = success_url
        self.failure_url = failure_url
        self.expires_url = expires_url
        self.external_reference = external_reference
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.expires_at = expires_at
    
    def __repr__(self):
        return f"<Checkout {self.name} - {self.client.name} - R$ {self.value}>"
    
    def is_expired(self) -> bool:
        """Verifica se o checkout expirou"""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False
    
    def is_paid(self) -> bool:
        """Verifica se o checkout foi pago"""
        return self.status == 'PAID'
    
    def can_be_cancelled(self) -> bool:
        """Verifica se o checkout pode ser cancelado"""
        return self.status in ['PENDING'] and not self.is_expired()
    
    def mark_as_paid(self):
        """Marca o checkout como pago"""
        if self.status in ['PENDING', 'RECEIVED']:
            self.status = 'PAID'
            self.updated_at = datetime.now()
    
    def mark_as_received(self):
        """Marca o checkout como recebido (PIX)"""
        if self.status == 'PENDING':
            self.status = 'RECEIVED'
            self.updated_at = datetime.now()
    
    def mark_as_refunded(self):
        """Marca o checkout como estornado"""
        if self.status in ['PAID', 'RECEIVED', 'REFUNDING']:
            self.status = 'REFUNDED'
            self.updated_at = datetime.now()
    
    def mark_as_failed(self):
        """Marca o checkout como falhou"""
        if self.status in ['PENDING']:
            self.status = 'FAILED'
            self.updated_at = datetime.now()
    
    def cancel(self):
        """Cancela o checkout"""
        if self.can_be_cancelled():
            self.status = 'CANCELLED'
            self.updated_at = datetime.now()
    
    def expire(self):
        """Expira o checkout"""
        if self.status == 'PENDING':
            self.status = 'EXPIRED'
            self.updated_at = datetime.now()
    
    def set_asaas_data(self, asaas_id: str, checkout_url: str):
        """Define os dados retornados pelo ASAAS"""
        self.asaas_id = asaas_id
        self.checkout_url = checkout_url
        self.updated_at = datetime.now()
