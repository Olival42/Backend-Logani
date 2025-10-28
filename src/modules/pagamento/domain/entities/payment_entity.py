from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from modules.cliente.domain.entities.client_entity import Client as ClientEntity


class Payment:
    """
    Entidade de domínio para Pagamento
    """
    
    def __init__(
        self,
        id: str,
        client: ClientEntity,
        value: Decimal,
        payment_method: str,
        order_id: Optional[str] = None,
        asaas_id: Optional[str] = None,
        asaas_checkout_id: Optional[str] = None,
        status: str = 'PENDING',
        description: Optional[str] = None,
        checkout_url: Optional[str] = None,
        payment_url: Optional[str] = None,
        external_reference: Optional[str] = None,
        installments: int = 1,
        expires_at: Optional[datetime] = None,
        paid_at: Optional[datetime] = None,
        refunded_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs
    ):
        self.id = id
        self.client = client
        self.order_id = order_id
        self.value = value
        self.payment_method = payment_method
        self.asaas_id = asaas_id
        self.asaas_checkout_id = asaas_checkout_id
        self.status = status
        self.description = description
        self.checkout_url = checkout_url
        self.payment_url = payment_url
        self.external_reference = external_reference
        self.installments = installments
        self.installment_id = kwargs.get('installment_id')
        self.installment_number = kwargs.get('installment_number')
        self.expires_at = expires_at
        self.paid_at = paid_at
        self.refunded_at = refunded_at
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at
    
    def __repr__(self):
        return f"<Payment R$ {self.value} - {self.status}>"
    
    def is_pending(self) -> bool:
        """Verifica se o pagamento está pendente"""
        return self.status == 'PENDING'
    
    def is_paid(self) -> bool:
        """Verifica se o pagamento foi pago"""
        return self.status in ['PAID', 'RECEIVED']
    
    def is_expired(self) -> bool:
        """Verifica se o pagamento expirou"""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False
    
    def can_be_cancelled(self) -> bool:
        """Verifica se o pagamento pode ser cancelado"""
        return self.status == 'PENDING' and not self.is_expired()
    
    def can_be_refunded(self) -> bool:
        """Verifica se o pagamento pode ser estornado"""
        return self.status in ['PAID', 'RECEIVED']
    
    def mark_as_paid(self):
        """Marca o pagamento como pago"""
        if self.status in ['PENDING', 'RECEIVED']:
            self.status = 'PAID'
            self.paid_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_received(self):
        """Marca o pagamento como recebido (PIX)"""
        if self.status == 'PENDING':
            self.status = 'RECEIVED'
            self.paid_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_refunded(self):
        """Marca o pagamento como estornado"""
        if self.status in ['PAID', 'RECEIVED', 'REFUNDING']:
            self.status = 'REFUNDED'
            self.refunded_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_failed(self):
        """Marca o pagamento como falhou"""
        if self.status == 'PENDING':
            self.status = 'FAILED'
            self.updated_at = datetime.now(timezone.utc)
    
    def cancel(self):
        """Cancela o pagamento"""
        if self.can_be_cancelled():
            self.status = 'CANCELLED'
            self.updated_at = datetime.now(timezone.utc)
    
    def expire(self):
        """Expira o pagamento"""
        if self.status == 'PENDING':
            self.status = 'EXPIRED'
            self.updated_at = datetime.now(timezone.utc)
    
    def set_asaas_data(self, asaas_id: str, checkout_url: Optional[str] = None):
        """Define os dados retornados pelo Asaas"""
        self.asaas_id = asaas_id
        if checkout_url:
            self.checkout_url = checkout_url
        self.updated_at = datetime.now()

