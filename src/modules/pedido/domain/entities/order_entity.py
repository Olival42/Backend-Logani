from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from modules.cliente.domain.entities.client_entity import Client as ClientEntity


class OrderItem:
    """
    Entidade de domínio para item do pedido
    """
    
    def __init__(
        self,
        product_id: str,
        product_name: str,
        quantity: int,
        unit_price: Decimal,
        total_price: Optional[Decimal] = None
    ):
        self.product_id = product_id
        self.product_name = product_name
        self.quantity = quantity
        self.unit_price = unit_price
        self.total_price = total_price or (unit_price * Decimal(str(quantity)))
    
    def __repr__(self):
        return f"<OrderItem {self.product_name} x {self.quantity}>"


class Order:
    """
    Entidade de domínio para Pedido
    """
    
    def __init__(
        self,
        id: str,
        client: ClientEntity,
        items: List[OrderItem],
        subtotal: Decimal,
        total: Optional[Decimal] = None,
        status: str = 'PENDING',
        external_reference: Optional[str] = None,
        notes: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        confirmed_at: Optional[datetime] = None
    ):
        self.id = id
        self.client = client
        self.items = items
        self.subtotal = subtotal
        self.total = total or subtotal
        self.status = status
        self.external_reference = external_reference
        self.notes = notes
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at
        self.confirmed_at = confirmed_at
    
    def __repr__(self):
        return f"<Order {self.external_reference or self.id} - {self.client.name} - R$ {self.total}>"
    
    def is_pending(self) -> bool:
        """Verifica se o pedido está pendente"""
        return self.status == 'PENDING'
    
    def is_confirmed(self) -> bool:
        """Verifica se o pedido está confirmado"""
        return self.status == 'CONFIRMED'
    
    def is_cancelled(self) -> bool:
        """Verifica se o pedido está cancelado"""
        return self.status == 'CANCELLED'
    
    def is_paid(self) -> bool:
        """Verifica se o pedido está pago"""
        return self.status == 'PAID'
    
    def can_be_cancelled(self) -> bool:
        """Verifica se o pedido pode ser cancelado"""
        return self.status in ['PENDING', 'CONFIRMED']
    
    def confirm(self):
        """Confirma o pedido"""
        if self.status == 'PENDING':
            self.status = 'CONFIRMED'
            self.confirmed_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_paid(self):
        """Marca o pedido como pago"""
        if self.status in ['PENDING', 'CONFIRMED']:
            self.status = 'PAID'
            if not self.confirmed_at:
                self.confirmed_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
    
    def cancel(self):
        """Cancela o pedido"""
        if self.can_be_cancelled():
            self.status = 'CANCELLED'
            self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_preparing(self):
        """Marca o pedido como em preparação"""
        if self.status == 'CONFIRMED':
            self.status = 'PREPARING'
            self.updated_at = datetime.now(timezone.utc)
    
    def total_items(self) -> int:
        """Retorna a quantidade total de itens"""
        return sum(item.quantity for item in self.items)

