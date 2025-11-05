from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from django.conf import settings
from django.db import transaction

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
        
        # Salva com transação atômica para garantir que pedido e itens sejam salvos juntos
        with transaction.atomic():
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
            'active': saved_order.active,
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
        
        # Usa transação atômica para garantir consistência
        with transaction.atomic():
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
        
        # Verifica se o pedido está ativo
        if not order.active:
            raise ValueError("Não é possível cancelar um pedido inativo")
        
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
        
        # Usa transação atômica para garantir que se o envio de email falhar, nada seja salvo
        with transaction.atomic():
            # Cancela o pedido
            order.cancel()
            updated_order = self.order_repository.update(order)
            
            # Envia emails de notificação de cancelamento de forma assíncrona
            try:
                # Serializa dados para enviar para as tasks
                order_data = self._serialize_order(updated_order)
                client_data = self._serialize_client(updated_order.client)
                
                # Chama tasks Celery assíncronas
                from modules.email.tasks import (
                    send_order_cancelled_email_async,
                    send_order_cancelled_email_to_customer_async
                )
                
                # Envia emails em background com retry
                try:
                    email_task_1 = send_order_cancelled_email_async.delay(order_data, client_data, refund_results)
                    email_task_2 = send_order_cancelled_email_to_customer_async.delay(order_data, client_data)
                except Exception as e:
                    # Se falhar ao agendar as tasks, tenta novamente
                    try:
                        email_task_1 = send_order_cancelled_email_async.apply_async(
                            args=[order_data, client_data, refund_results],
                            countdown=2  # Espera 2 segundos antes de tentar novamente
                        )
                        email_task_2 = send_order_cancelled_email_to_customer_async.apply_async(
                            args=[order_data, client_data],
                            countdown=2
                        )
                    except Exception as retry_error:
                        # Se ainda falhar, cancela a transação
                        raise ValueError("Não foi possível agendar o envio de emails. Operação cancelada.")
                
            except Exception as e:
                # Se qualquer parte do envio falhar, faz rollback
                raise ValueError(f"Não foi possível enviar emails de cancelamento: {str(e)}")
        
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
        
        # Usa transação atômica para garantir consistência
        with transaction.atomic():
            order.mark_as_preparing()
            updated_order = self.order_repository.update(order)
        
        return {
            'order_id': str(updated_order.id),
            'external_reference': updated_order.external_reference,
            'status': updated_order.status
        }
    
    def update_order_items(
        self,
        order_id: str,
        items_actions: List[Dict[str, Any]],
        produto_repository
    ) -> Dict[str, Any]:
        """
        Atualiza itens de um pedido (adicionar, remover, atualizar quantidade)
        Apenas para pedidos PENDING
        
        Args:
            order_id: ID do pedido
            items_actions: Lista de ações [{action: 'add'|'update'|'remove', product_id, quantity?}]
            produto_repository: Repositório de produtos para buscar informações
            
        Returns:
            Dict com informações do pedido atualizado
        """
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError("Pedido não encontrado")
        
        # Valida que o pedido está pendente
        if order.status != 'PENDING':
            raise ValueError(f"Pedido não pode ser atualizado. Status atual: {order.status}. Apenas pedidos PENDING podem ser atualizados.")
        
        # Cria cópia da lista de itens atual para manipulação
        updated_items = list(order.items)
        
        # Processa cada ação
        for action_data in items_actions:
            action = action_data['action']
            product_id = action_data['product_id']
            quantity = action_data.get('quantity')
            
            # Busca produto se for adicionar
            if action in ['add', 'update']:
                product = produto_repository.get_by_id(product_id)
                if not product:
                    raise ValueError(f"Produto com ID '{product_id}' não encontrado")
            
            if action == 'add':
                # Verifica se o produto já existe no pedido
                existing_item = None
                for item in updated_items:
                    if item.product_id == product_id:
                        existing_item = item
                        break
                
                if existing_item:
                    # Se já existe, atualiza a quantidade
                    new_quantity = existing_item.quantity + quantity
                    existing_item.quantity = new_quantity
                    existing_item.total_price = existing_item.unit_price * Decimal(str(new_quantity))
                else:
                    # Se não existe, adiciona novo item
                    unit_price = Decimal(str(product.preco))
                    total_price = unit_price * Decimal(str(quantity))
                    new_item = OrderItem(
                        product_id=product.id,
                        product_name=product.nome,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                    updated_items.append(new_item)
            
            elif action == 'update':
                # Atualiza quantidade de um item existente
                item_found = False
                for item in updated_items:
                    if item.product_id == product_id:
                        item.quantity = quantity
                        item.total_price = item.unit_price * Decimal(str(quantity))
                        item_found = True
                        break
                
                if not item_found:
                    raise ValueError(f"Produto com ID '{product_id}' não encontrado no pedido para atualização")
            
            elif action == 'remove':
                # Remove item do pedido
                item_to_remove = None
                for item in updated_items:
                    if item.product_id == product_id:
                        item_to_remove = item
                        break
                
                if not item_to_remove:
                    raise ValueError(f"Produto com ID '{product_id}' não encontrado no pedido para remoção")
                
                updated_items.remove(item_to_remove)
        
        # Se todos os itens foram removidos, marca pedido como inativo
        if not updated_items:
            order.items = []
            order.subtotal = Decimal('0')
            order.total = Decimal('0')
            order.mark_as_inactive()
        else:
            # Recalcula subtotal e total
            subtotal = Decimal('0')
            for item in updated_items:
                subtotal += item.total_price
            
            # Atualiza o pedido com os novos itens
            order.items = updated_items
            order.subtotal = subtotal
            order.total = subtotal
        
        order.updated_at = datetime.now(timezone.utc)
        
        # Salva com transação atômica
        with transaction.atomic():
            updated_order = self.order_repository.update(order)
        
        # Prepara resposta
        items_data = [
            {
                'product_id': item.product_id,
                'product_name': item.product_name,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price)
            }
            for item in updated_order.items
        ]
        
        result = {
            'order_id': str(updated_order.id),
            'external_reference': updated_order.external_reference,
            'client': {
                'id': str(updated_order.client.id),
                'name': updated_order.client.name
            },
            'items': items_data,
            'subtotal': float(updated_order.subtotal),
            'total': float(updated_order.total),
            'total_items': updated_order.total_items(),
            'status': updated_order.status,
            'active': updated_order.active,
            'notes': updated_order.notes,
            'created_at': updated_order.created_at.isoformat() if updated_order.created_at else None,
            'updated_at': updated_order.updated_at.isoformat() if updated_order.updated_at else None,
            'confirmed_at': updated_order.confirmed_at.isoformat() if updated_order.confirmed_at else None
        }
        
        # Se o pedido foi inativado, adiciona mensagem informativa
        if not updated_order.active:
            result['message'] = 'Pedido marcado como inativo porque todos os itens foram removidos'
        
        return result
    
    def _serialize_order(self, order: Order) -> Dict[str, Any]:
        """Serializa entidade Order para Dict"""
        items_data = [
            {
                'product_id': item.product_id,
                'product_name': item.product_name,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price)
            }
            for item in order.items
        ]
        
        return {
            'id': str(order.id),
            'external_reference': order.external_reference,
            'subtotal': float(order.subtotal),
            'total': float(order.total),
            'status': order.status,
            'notes': order.notes,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'updated_at': order.updated_at.isoformat() if order.updated_at else None,
            'confirmed_at': order.confirmed_at.isoformat() if order.confirmed_at else None,
            'items': items_data
        }
    
    def _serialize_client(self, client: 'Client') -> Dict[str, Any]:
        """Serializa entidade Client para Dict"""
        address_data = {}
        if client.address:
            address_data = {
                'address': client.address.address,
                'number': client.address.number,
                'complement': client.address.complement or '',
                'province': client.address.province,
                'city': client.address.city,
                'state': client.address.state,
                'postal_code': client.address.postal_code
            }
        
        return {
            'id': str(client.id),
            'name': client.name,
            'cpf': client.cpf,
            'phone': client.phone,
            'mobile_phone': client.mobile_phone,
            'email': client.email,
            'address': address_data
        }

