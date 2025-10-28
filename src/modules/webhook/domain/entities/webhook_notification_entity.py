from typing import Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal


class WebhookNotification:
    """
    Entidade de domínio para notificações de webhook recebidas do ASAAS
    """
    
    def __init__(
        self,
        id: Optional[str] = None,
        event: str = None,
        payment_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        installment_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        payment_date: Optional[datetime] = None,
        due_date: Optional[datetime] = None,
        value: Optional[Decimal] = None,
        net_value: Optional[Decimal] = None,
        original_value: Optional[Decimal] = None,
        interest_value: Optional[Decimal] = None,
        description: Optional[str] = None,
        external_reference: Optional[str] = None,
        billing_type: Optional[str] = None,
        status: Optional[str] = None,
        checkout_session: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        processed: bool = False,
        processed_at: Optional[datetime] = None,
    ):
        self.id = id
        self.event = event
        self.payment_id = payment_id
        self.subscription_id = subscription_id
        self.installment_id = installment_id
        self.customer_id = customer_id
        self.payment_date = payment_date
        self.due_date = due_date
        self.value = value
        self.net_value = net_value
        self.original_value = original_value
        self.interest_value = interest_value
        self.description = description
        self.external_reference = external_reference
        self.billing_type = billing_type
        self.status = status
        self.checkout_session = checkout_session
        self.data = data or {}
        self.created_at = created_at or datetime.now(timezone.utc)
        self.processed = processed
        self.processed_at = processed_at
    
    def mark_as_processed(self):
        """Marca a notificação como processada"""
        self.processed = True
        self.processed_at = datetime.now(timezone.utc)
    
    def __repr__(self):
        return f"<WebhookNotification {self.event} - {self.external_reference} - {self.status}>"

