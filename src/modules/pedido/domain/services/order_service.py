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
        notes: Optional[str] = None,
        discount_amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Cria um novo pedido
        
        Args:
            client: Entidade do cliente
            items: Lista de itens [{product_id, product_name, quantity, unit_price}]
            notes: Observações adicionais
            discount_amount: Valor do desconto a ser aplicado (opcional)
            
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
        
        # Aplica desconto se fornecido
        discount = discount_amount or Decimal('0.00')
        if discount > subtotal:
            discount = subtotal  # Garante que o desconto não seja maior que o subtotal
        
        # Calcula total com desconto
        total = subtotal - discount
        if total < Decimal('0.00'):
            total = Decimal('0.00')
        
        # Gera referência externa
        external_reference = f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid4())[:8].upper()}"
        
        # Adiciona informação do desconto nas notas se aplicado
        final_notes = notes or ""
        if discount > Decimal('0.00'):
            discount_note = f"\n\nCupom de desconto aplicado: R$ {discount:.2f}"
            final_notes = final_notes + discount_note if final_notes else discount_note.strip()
        
        # Cria entidade de pedido
        order = Order(
            id=str(uuid4()),
            client=client,
            items=order_items,
            subtotal=subtotal,
            total=total,
            external_reference=external_reference,
            notes=final_notes
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
        processed_installments = set()
        payment_repository = None
        
        if payments:
            from modules.pagamento.adapters.persistence.payment_repository_django import PaymentRepository
            payment_repository = PaymentRepository()
        
        # Se deve estornar e existem pagamentos, processa estorno
        asaas_client = None
        if should_refund and payments:
            from modules.cliente.adapters.external.asaas_client import AsaasClient
            asaas_client = AsaasClient()
        
        for payment_data in payments:
            payment = payment_repository.get_by_id(payment_data['id']) if payment_repository else None
            payment_status = payment_data.get('status')
            has_asaas_reference = payment_data.get('asaas_id') or payment_data.get('installment_id')
            is_paid_status = payment_status in ['PAID', 'RECEIVED', 'REFUNDING']
            
            # Processa estorno quando solicitado e possível
            if should_refund and asaas_client and payment and has_asaas_reference and is_paid_status:
                is_installment = payment.installments > 1 and payment.installment_id
                
                if is_installment and payment.installment_id:
                    installment_id = payment.installment_id
                    
                    if installment_id in processed_installments:
                        # Já estornamos este parcelamento anteriormente, apenas garante status local
                        if payment.status not in ['REFUNDED', 'CANCELLED']:
                            payment.mark_as_refunded()
                            payment_repository.update(payment)
                        continue
                    
                    try:
                        refund_response = asaas_client.refund_installment(
                            installment_id=installment_id,
                            description=f"Estorno automático por cancelamento do pedido {order.external_reference}"
                        )
                        
                        # Atualiza todos os pagamentos do parcelamento como estornados
                        installment_payments = payment_repository.get_by_installment_id(installment_id)
                        for installment_payment in installment_payments:
                            installment_payment.mark_as_refunded()
                            payment_repository.update(installment_payment)
                        
                        refund_results.append({
                            'payment_id': payment_data['id'],
                            'type': 'installment',
                            'installment_id': installment_id,
                            'status': 'REFUNDED',
                            'response': refund_response
                        })
                        processed_installments.add(installment_id)
                        continue
                    except Exception as e:
                        refund_results.append({
                            'payment_id': payment_data['id'],
                            'type': 'installment',
                            'installment_id': installment_id,
                            'error': str(e)
                        })
                        continue
                
                if payment and payment.asaas_id:
                    try:
                        refund_response = asaas_client.refund_payment(
                            payment_id=payment.asaas_id,
                            description=f"Estorno automático por cancelamento do pedido {order.external_reference}"
                        )
                        
                        payment.mark_as_refunded()
                        payment_repository.update(payment)
                        
                        refund_results.append({
                            'payment_id': payment_data['id'],
                            'type': 'single_payment',
                            'status': 'REFUNDED',
                            'response': refund_response
                        })
                        continue
                    except Exception as e:
                        refund_results.append({
                            'payment_id': payment_data['id'],
                            'type': 'single_payment',
                            'error': str(e)
                        })
            
            # Se não foi possível estornar, tenta cancelar localmente pagamentos ainda pendentes
            if payment and payment.status not in ['REFUNDED', 'CANCELLED']:
                if payment.can_be_cancelled():
                    payment.cancel()
                    payment_repository.update(payment)
                    refund_results.append({
                        'payment_id': payment_data['id'],
                        'type': 'cancelled',
                        'status': payment.status
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
        items_actions: Optional[List[Dict[str, Any]]] = None,
        produto_repository = None,
        coupon_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Atualiza itens de um pedido (adicionar, remover, atualizar quantidade) e/ou aplica cupom
        Apenas para pedidos PENDING
        
        Args:
            order_id: ID do pedido
            items_actions: Lista de ações [{action: 'add'|'update'|'remove', product_id, quantity?}] (opcional)
            produto_repository: Repositório de produtos para buscar informações (opcional se não houver items)
            coupon_code: Código do cupom de desconto a ser aplicado (opcional)
            
        Returns:
            Dict com informações do pedido atualizado
        """
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError("Pedido não encontrado")
        
        # Valida que o pedido está pendente
        if order.status != 'PENDING':
            raise ValueError(f"Pedido não pode ser atualizado. Status atual: {order.status}. Apenas pedidos PENDING podem ser atualizados.")
        
        # Valida que pelo menos items ou coupon_code foi fornecido
        if not items_actions and not coupon_code:
            raise ValueError("É necessário informar pelo menos 'items' ou 'coupon_code'.")
        
        # Cria cópia da lista de itens atual para manipulação
        updated_items = list(order.items)
        
        # Garante revalidação de cupom ao alterar itens
        coupon_already_applied = bool(order.notes and "Cupom de desconto aplicado" in order.notes)
        if items_actions and coupon_already_applied and not coupon_code:
            raise ValueError("Pedido possui desconto aplicado. Reenvie o cupom para revalidar ao alterar os itens.")
        
        # Variável para armazenar informações do cupom aplicado
        discount_info = None
        
        # Processa ações nos itens se fornecidas
        if items_actions:
            if not produto_repository:
                raise ValueError("produto_repository é obrigatório quando items_actions é fornecido")
                
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
                    
                    product_is_active = True
                    if hasattr(product, 'ativo'):
                        product_is_active = bool(getattr(product, 'ativo'))
                    elif hasattr(product, 'active'):
                        product_is_active = bool(getattr(product, 'active'))
                    elif hasattr(product, 'is_active'):
                        attr = getattr(product, 'is_active')
                        product_is_active = attr() if callable(attr) else bool(attr)
                    
                    if not product_is_active:
                        raise ValueError(
                            f"Produto '{getattr(product, 'nome', product_id)}' está inativo e não pode ser utilizado no pedido."
                        )
                
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
        else:
            # Se não há ações nos itens, mantém os itens atuais
            pass
        
        # Se todos os itens foram removidos, marca pedido como inativo
        if not updated_items:
            order.items = []
            order.subtotal = Decimal('0')
            order.total = Decimal('0')
            order.mark_as_inactive()
        else:
            # Recalcula subtotal (se items foram alterados) ou usa o atual
            if items_actions:
                # Recalcula subtotal baseado nos itens atualizados
                subtotal = Decimal('0')
                for item in updated_items:
                    subtotal += item.total_price
            else:
                # Se não houve mudanças nos itens, usa o subtotal atual
                subtotal = order.subtotal
            
            # Calcula desconto atual (se houver) baseado na diferença entre subtotal e total
            # Se subtotal != total, significa que já existe desconto aplicado
            current_discount = order.subtotal - order.total
            if current_discount < Decimal('0.00'):
                current_discount = Decimal('0.00')
            
            # Aplica cupom se fornecido
            discount_amount = Decimal('0.00')
            if coupon_code:
                try:
                    from modules.checkout.domain.services.coupon_service import CouponService
                    coupon_service = CouponService()
                    
                    # Valida e calcula desconto baseado no novo subtotal
                    discount_info = coupon_service.calculate_discount(
                        coupon_code,
                        subtotal,
                        client_id=str(order.client.id)
                    )
                    discount_amount = discount_info['discount_amount']
                    
                    # Atualiza notas com informação do cupom
                    # Remove informação de cupom anterior se existir
                    notes_clean = order.notes or ""
                    if "Cupom de desconto aplicado:" in notes_clean:
                        # Remove linha do cupom anterior
                        lines = notes_clean.split('\n')
                        notes_clean = '\n'.join([line for line in lines if "Cupom de desconto aplicado:" not in line])
                    
                    # Adiciona nova informação do cupom
                    discount_note = f"\n\nCupom de desconto aplicado: R$ {discount_amount:.2f}"
                    if discount_info:
                        discount_note += f" ({discount_info['coupon_info']['code']} - {discount_info['coupon_info']['description']})"
                    order.notes = notes_clean + discount_note if notes_clean else discount_note.strip()
                    
                except ValueError as e:
                    raise ValueError(f"Erro ao aplicar cupom: {str(e)}")
                except Exception as e:
                    raise ValueError(f"Erro ao processar cupom: {str(e)}")
            
            # Calcula total com desconto
            total = subtotal - discount_amount
            if total < Decimal('0.00'):
                total = Decimal('0.00')
            
            # Atualiza o pedido com os novos itens
            order.items = updated_items
            order.subtotal = subtotal
            order.total = total
        
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
        
        # Adiciona informação do cupom na resposta se aplicado
        if discount_info:
            result['coupon_applied'] = {
                'code': discount_info['coupon_info']['code'],
                'description': discount_info['coupon_info']['description'],
                'discount_amount': float(discount_info['discount_amount']),
                'original_subtotal': float(discount_info['coupon_info']['original_value']),
                'final_total': float(discount_info['final_value'])
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
        
        shipping_data = None
        shipping_price = None
        if order.shipping:
            shipping_data = {
                'service_id': order.shipping.service_id,
                'service_name': order.shipping.service_name,
                'price': float(order.shipping.price),
                'custom_price': float(order.shipping.custom_price) if order.shipping.custom_price is not None else None,
                'final_price': float(order.shipping.final_price),
                'delivery_time': order.shipping.delivery_time,
                'custom_delivery_time': order.shipping.custom_delivery_time,
                'final_delivery_time': order.shipping.final_delivery_time,
                'currency': order.shipping.currency,
                'company': order.shipping.company,
                'from_postal_code': order.shipping.from_postal_code,
                'to_postal_code': order.shipping.to_postal_code
            }
            shipping_price = float(order.shipping.final_price)

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
            'items': items_data,
            'shipping': shipping_data,
            'shipping_price': shipping_price
        }
    
    def add_shipping_to_order(
        self,
        order_id: str,
        shipping_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adiciona um serviço de frete ao pedido
        
        Args:
            order_id: ID do pedido
            shipping_data: Dados do serviço de frete escolhido {
                'service_id': int,
                'service_name': str,
                'price': Decimal,
                'custom_price': Optional[Decimal],
                'delivery_time': int,
                'custom_delivery_time': Optional[int],
                'currency': str,
                'company': Optional[dict],
                'from_postal_code': str,
                'to_postal_code': str
            }
            
        Returns:
            Dict com informações do pedido atualizado com frete
        """
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError("Pedido não encontrado")
        
        # Valida que o pedido está pendente
        if order.status != 'PENDING':
            raise ValueError(
                f"Pedido não pode receber frete. Status atual: {order.status}. "
                "Apenas pedidos PENDING podem receber frete."
            )
        
        # Verifica se já existe frete no pedido
        from modules.pedido.adapters.persistence.models import OrderShipping as OrderShippingModel
        existing_shipping_price = Decimal('0.00')
        try:
            existing_shipping = OrderShippingModel.objects.get(order_id=order_id)
            # Remove frete existente para substituir
            existing_shipping_price = Decimal(str(existing_shipping.final_price))
            existing_shipping.delete()
        except OrderShippingModel.DoesNotExist:
            pass
        
        # Calcula o desconto atual (se houver)
        # O desconto é a diferença entre subtotal e total (sem considerar frete)
        # Se já existe frete, precisa removê-lo do total antes de calcular o desconto
        total_without_shipping = order.total - existing_shipping_price
        current_discount = order.subtotal - total_without_shipping
        if current_discount < Decimal('0.00'):
            current_discount = Decimal('0.00')
        
        # Calcula o total dos produtos com desconto (sem frete)
        products_total_with_discount = order.subtotal - current_discount
        
        # Calcula preço final do frete
        shipping_price = Decimal(str(shipping_data.get('custom_price') or shipping_data['price']))
        
        # Atualiza o total do pedido: (subtotal - desconto) + frete
        new_total = products_total_with_discount + shipping_price
        order.total = new_total
        order.updated_at = datetime.now(timezone.utc)
        
        # Salva pedido atualizado
        with transaction.atomic():
            updated_order = self.order_repository.update(order)
            
            # Cria o registro de frete
            OrderShippingModel.objects.create(
                id=str(uuid4()),
                order_id=updated_order.id,
                service_id=shipping_data['service_id'],
                service_name=shipping_data['service_name'],
                price=Decimal(str(shipping_data['price'])),
                custom_price=Decimal(str(shipping_data['custom_price'])) if shipping_data.get('custom_price') else None,
                delivery_time=shipping_data['delivery_time'],
                custom_delivery_time=shipping_data.get('custom_delivery_time'),
                currency=shipping_data.get('currency', 'BRL'),
                company=shipping_data.get('company'),
                from_postal_code=shipping_data['from_postal_code'],
                to_postal_code=shipping_data['to_postal_code']
            )
        
        # Busca o frete criado para retornar
        shipping = OrderShippingModel.objects.get(order_id=updated_order.id)
        
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
        
        shipping_data_response = {
            'service_id': shipping.service_id,
            'service_name': shipping.service_name,
            'price': float(shipping.price),
            'custom_price': float(shipping.custom_price) if shipping.custom_price else None,
            'final_price': float(shipping.final_price),
            'delivery_time': shipping.delivery_time,
            'custom_delivery_time': shipping.custom_delivery_time,
            'final_delivery_time': shipping.final_delivery_time,
            'currency': shipping.currency,
            'company': shipping.company,
            'from_postal_code': shipping.from_postal_code,
            'to_postal_code': shipping.to_postal_code
        }
        
        return {
            'order_id': str(updated_order.id),
            'external_reference': updated_order.external_reference,
            'client': {
                'id': str(updated_order.client.id),
                'name': updated_order.client.name
            },
            'items': items_data,
            'subtotal': float(updated_order.subtotal),
            'shipping': shipping_data_response,
            'shipping_price': float(shipping.final_price),
            'total': float(updated_order.total),
            'total_items': updated_order.total_items(),
            'status': updated_order.status,
            'active': updated_order.active,
            'notes': updated_order.notes,
            'created_at': updated_order.created_at.isoformat() if updated_order.created_at else None,
            'updated_at': updated_order.updated_at.isoformat() if updated_order.updated_at else None,
            'confirmed_at': updated_order.confirmed_at.isoformat() if updated_order.confirmed_at else None
        }
    
    def _serialize_client(self, client: ClientEntity) -> Dict[str, Any]:
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
            'email': client.email or (client.user.email if getattr(client, 'user', None) else None),
            'address': address_data
        }

