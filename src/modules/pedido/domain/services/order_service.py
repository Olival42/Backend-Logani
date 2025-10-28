from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from modules.pedido.domain.entities.order_entity import Order, OrderItem
from modules.pedido.domain.repositories.order_repository import IOrderRepository
from modules.cliente.domain.entities.client_entity import Client as ClientEntity


def _get_payments_for_order(order_id: str) -> List[Dict[str, Any]]:
    """Busca pagamentos relacionados a um pedido"""
    try:
        from modules.pagamento.adapters.persistence.payment_repository_django import PaymentRepository
        payment_repository = PaymentRepository()
        payments = payment_repository.get_by_order(order_id)
        
        return [
            {
                'id': str(payment.id),
                'value': float(payment.value),
                'payment_method': payment.payment_method,
                'status': payment.status,
                'installments': payment.installments,
                'checkout_url': payment.checkout_url,
                'created_at': payment.created_at.isoformat() if payment.created_at else None,
                'paid_at': payment.paid_at.isoformat() if payment.paid_at else None
            }
            for payment in payments
        ]
    except:
        return []


class OrderService:
    """
    Serviço de domínio para gerenciamento de pedidos
    """
    
    def __init__(self, order_repository: IOrderRepository):
        self.order_repository = order_repository
    
    def create_order(
        self,
        client: ClientEntity,
        items: List[Dict[str, Any]],
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cria um novo pedido
        
        Args:
            client: Entidade do cliente
            items: Lista de itens [{product_id, product_name, quantity, unit_price}]
            notes: Observações adicionais
            
        Returns:
            Dict com informações do pedido criado
        """
        # Processa itens
        order_items = []
        subtotal = Decimal('0')
        
        for item in items:
            quantity = int(item['quantity'])
            unit_price = Decimal(str(item['unit_price']))
            total_price = unit_price * Decimal(str(quantity))
            
            order_item = OrderItem(
                product_id=item['product_id'],
                product_name=item['product_name'],
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            order_items.append(order_item)
            subtotal += total_price
        
        # Gera referência externa
        external_reference = f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid4())[:8].upper()}"
        
        # Cria entidade de pedido
        order = Order(
            id=str(uuid4()),
            client=client,
            items=order_items,
            subtotal=subtotal,
            total=subtotal,
            external_reference=external_reference,
            notes=notes
        )
        
        # Salva
        saved_order = self.order_repository.save(order)
        
        # Prepara lista de itens para a resposta
        items_data = [
            {
                'product_id': item.product_id,
                'product_name': item.product_name,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price)
            }
            for item in saved_order.items
        ]
        
        return {
            'order_id': str(saved_order.id),
            'external_reference': saved_order.external_reference,
            'client': {
                'id': str(saved_order.client.id),
                'name': saved_order.client.name
            },
            'items': items_data,
            'subtotal': float(saved_order.subtotal),
            'total': float(saved_order.total),
            'total_items': saved_order.total_items(),
            'status': saved_order.status,
            'notes': saved_order.notes,
            'created_at': saved_order.created_at.isoformat() if saved_order.created_at else None,
            'updated_at': saved_order.updated_at.isoformat() if saved_order.updated_at else None,
            'confirmed_at': saved_order.confirmed_at.isoformat() if saved_order.confirmed_at else None
        }
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Busca um pedido por ID"""
        return self.order_repository.get_by_id(order_id)
    
    def get_order_by_reference(self, external_reference: str) -> Optional[Order]:
        """Busca um pedido por referência externa"""
        return self.order_repository.get_by_external_reference(external_reference)
    
    def get_client_orders(self, client_id: str) -> List[Order]:
        """Busca pedidos de um cliente"""
        return self.order_repository.get_by_client(client_id)
    
    def confirm_order(self, order_id: str) -> Dict[str, Any]:
        """
        Confirma um pedido (quando o pagamento é confirmado)
        
        Args:
            order_id: ID do pedido
            
        Returns:
            Dict com informações da confirmação
        """
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError("Pedido não encontrado")
        
        if order.status != 'PENDING':
            raise ValueError(f"Pedido não pode ser confirmado. Status atual: {order.status}")
        
        order.confirm()
        updated_order = self.order_repository.update(order)
        
        return {
            'order_id': str(updated_order.id),
            'external_reference': updated_order.external_reference,
            'status': updated_order.status,
            'confirmed_at': updated_order.confirmed_at.isoformat() if updated_order.confirmed_at else None
        }
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancela um pedido
        
        Args:
            order_id: ID do pedido
            
        Returns:
            Dict com informações do cancelamento
        """
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError("Pedido não encontrado")
        
        if not order.can_be_cancelled():
            raise ValueError(f"Pedido não pode ser cancelado. Status atual: {order.status}")
        
        order.cancel()
        updated_order = self.order_repository.update(order)
        
        return {
            'order_id': str(updated_order.id),
            'external_reference': updated_order.external_reference,
            'status': updated_order.status
        }
    
    def mark_order_as_preparing(self, order_id: str) -> Dict[str, Any]:
        """
        Marca o pedido como em preparação
        
        Args:
            order_id: ID do pedido
            
        Returns:
            Dict com informações da atualização
        """
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError("Pedido não encontrado")
        
        order.mark_as_preparing()
        updated_order = self.order_repository.update(order)
        
        return {
            'order_id': str(updated_order.id),
            'external_reference': updated_order.external_reference,
            'status': updated_order.status
        }
    

