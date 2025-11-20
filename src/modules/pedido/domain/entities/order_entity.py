from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from modules.cliente.domain.entities.client_entity import Client as ClientEntity


class OrderShipping:
    """
    Entidade para representar o frete associado a um pedido
    """

    def __init__(
        self,
        service_id: int,
        service_name: str,
        price: Decimal,
        custom_price: Optional[Decimal] = None,
        delivery_time: int = 0,
        custom_delivery_time: Optional[int] = None,
        currency: str = 'BRL',
        company: Optional[Dict[str, Any]] = None,
        from_postal_code: Optional[str] = None,
        to_postal_code: Optional[str] = None
    ):
        self.service_id = service_id
        self.service_name = service_name
        self.price = price
        self.custom_price = custom_price
        self.delivery_time = delivery_time
        self.custom_delivery_time = custom_delivery_time
        self.currency = currency
        self.company = company or {}
        self.from_postal_code = from_postal_code
        self.to_postal_code = to_postal_code

    @property
    def final_price(self) -> Decimal:
        """Retorna o preço final considerando custom_price quando disponível"""
        return self.custom_price if self.custom_price is not None else self.price

    @property
    def final_delivery_time(self) -> int:
        """Retorna o prazo final considerando custom_delivery_time quando disponível"""
        return self.custom_delivery_time if self.custom_delivery_time is not None else self.delivery_time


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
        confirmed_at: Optional[datetime] = None,
        active: bool = True,
        shipping: Optional[OrderShipping] = None
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
        self.active = active
        self.shipping = shipping
    
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
        return self.status in ['PENDING', 'CONFIRMED', 'PAID']
    
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
    
    def can_be_cancelled_with_time_check(self, days_to_cancel: int = 2):
        """
        Verifica se o pedido pode ser cancelado considerando o prazo
        
        Args:
            days_to_cancel: Número de dias permitidos para cancelamento
            
        Returns:
            Tuple (pode_cancelar, mensagem_erro)
        """
        if not self.can_be_cancelled():
            return False, f"Pedido não pode ser cancelado. Status atual: {self.status}"
        
        # Verifica prazo de cancelamento (apenas para pedidos confirmados ou pagos)
        if self.status in ['CONFIRMED', 'PAID'] and self.confirmed_at:
            # Calcula os dias decorridos desde a confirmação usando timezone UTC
            now = datetime.now(timezone.utc)
            days_passed = (now - self.confirmed_at).days
            
            if days_passed > days_to_cancel:
                return False, f"Prazo de cancelamento expirado. Pedido confirmado há {days_passed} dias. Prazo máximo: {days_to_cancel} dias"
        
        return True, None
    
    def mark_as_preparing(self):
        """Marca o pedido como em preparação"""
        if self.status == 'CONFIRMED':
            self.status = 'PREPARING'
            self.updated_at = datetime.now(timezone.utc)
    
    def total_items(self) -> int:
        """Retorna a quantidade total de itens"""
        return sum(item.quantity for item in self.items)
    
    def mark_as_inactive(self):
        """Marca o pedido como inativo"""
        self.active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def is_active(self) -> bool:
        """Verifica se o pedido está ativo"""
        return self.active

