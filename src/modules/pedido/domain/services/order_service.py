from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from django.conf import settings

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
                'installment_id': payment.installment_id,
                'installment_number': payment.installment_number,
                'asaas_id': payment.asaas_id,
                'asaas_checkout_id': payment.asaas_checkout_id,
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
    
    def cancel_order(self, order_id: str, should_refund: bool = True) -> Dict[str, Any]:
        """
        Cancela um pedido e estorna pagamentos quando aplicável
        
        Args:
            order_id: ID do pedido
            should_refund: Se True, estorna os pagamentos automaticamente
            
        Returns:
            Dict com informações do cancelamento
        """
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError("Pedido não encontrado")
        
        # Verifica se o pedido pode ser cancelado (incluindo verificação de prazo)
        days_to_cancel = getattr(settings, 'DAYS_TO_CANCEL', 2)
        can_cancel, error_message = order.can_be_cancelled_with_time_check(days_to_cancel)
        
        if not can_cancel:
            raise ValueError(error_message)
        
        # Busca pagamentos do pedido
        payments = _get_payments_for_order(order_id)
        refund_results = []
        
        # Se deve estornar e existem pagamentos, processa estorno
        if should_refund and payments:
            from modules.pagamento.adapters.persistence.payment_repository_django import PaymentRepository
            from modules.cliente.adapters.external.asaas_client import AsaasClient
            
            payment_repository = PaymentRepository()
            asaas_client = AsaasClient()
            
            for payment_data in payments:
                if payment_data['status'] in ['PAID', 'RECEIVED']:
                    try:
                        # Busca o pagamento pelo ID
                        payment = payment_repository.get_by_id(payment_data['id'])
                        
                        if payment and payment.asaas_id:
                            # Determina se é parcelado
                            is_installment = payment.installments > 1 and payment.installment_id
                            
                            if is_installment:
                                # Estorna parcelamento completo
                                installment_id = payment.installment_id
                                refund_response = asaas_client.refund_installment(
                                    installment_id=installment_id,
                                    description=f"Estorno automático por cancelamento do pedido {order.external_reference}"
                                )
                                refund_results.append({
                                    'payment_id': payment_data['id'],
                                    'type': 'installment',
                                    'installment_id': installment_id,
                                    'response': refund_response
                                })
                            else:
                                # Estorna pagamento único (PIX ou cartão 1 parcela)
                                refund_response = asaas_client.refund_payment(
                                    payment_id=payment.asaas_id,
                                    description=f"Estorno automático por cancelamento do pedido {order.external_reference}"
                                )
                                refund_results.append({
                                    'payment_id': payment_data['id'],
                                    'type': 'single_payment',
                                    'response': refund_response
                                })
                    except Exception as e:
                        refund_results.append({
                            'payment_id': payment_data['id'],
                            'error': str(e)
                        })
        
        # Cancela o pedido
        order.cancel()
        updated_order = self.order_repository.update(order)
        
        return {
            'order_id': str(updated_order.id),
            'external_reference': updated_order.external_reference,
            'status': updated_order.status,
            'refunds': refund_results
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
    

