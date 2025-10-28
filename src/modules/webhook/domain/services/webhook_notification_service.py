from typing import Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
import re

from modules.webhook.domain.entities.webhook_notification_entity import WebhookNotification
from modules.webhook.adapters.persistence.webhook_notification_repository_django import WebhookNotificationRepository
from modules.pagamento.domain.repositories.payment_repository import IPaymentRepository
from modules.pagamento.domain.entities.payment_entity import Payment
from modules.pedido.domain.repositories.order_repository import IOrderRepository
from modules.pedido.domain.entities.order_entity import Order


class WebhookNotificationService:
    """
    Serviço para processar notificações de webhook do Asaas
    """
    
    def __init__(
        self, 
        notification_repository: WebhookNotificationRepository, 
        payment_repository: IPaymentRepository,
        order_repository: IOrderRepository
    ):
        self.notification_repository = notification_repository
        self.payment_repository = payment_repository
        self.order_repository = order_repository
    
    def receive_and_save_notification(self, data: Dict[str, Any]) -> WebhookNotification:
        """
        Recebe e salva uma notificação de webhook do Asaas
        
        Args:
            data: Dados da notificação recebida
            
        Returns:
            Entidade WebhookNotification salva
        """
        # Extrai os campos principais da notificação
        event = data.get('event', 'UNKNOWN')
        payment = data.get('payment', {})
        
        notification = WebhookNotification(
            id=str(uuid4()),
            event=event,
            payment_id=payment.get('id'),
            subscription_id=payment.get('subscription'),
            installment_id=payment.get('installment'),
            customer_id=payment.get('customer'),
            payment_date=self._parse_datetime(payment.get('paymentDate')),
            due_date=self._parse_datetime(payment.get('dueDate')),
            value=self._parse_decimal(payment.get('value')),
            net_value=self._parse_decimal(payment.get('netValue')),
            original_value=self._parse_decimal(payment.get('originalValue')),
            interest_value=self._parse_decimal(payment.get('interestValue')),
            description=payment.get('description'),
            external_reference=payment.get('externalReference'),
            billing_type=payment.get('billingType'),
            status=payment.get('status'),
            checkout_session=payment.get('checkoutSession'),
            data=data
        )
        
        return self.notification_repository.save(notification)
    
    def process_notification(self, notification: WebhookNotification) -> Dict[str, Any]:
        """
        Processa uma notificação de webhook e atualiza o sistema
        
        Args:
            notification: Entidade WebhookNotification para processar
            
        Returns:
            Dict com o resultado do processamento
        """
        try:
            # Evita reprocessamento
            if notification.processed:
                return {
                    'success': True,
                    'message': 'Notificação já foi processada',
                    'notification_id': notification.id
                }
            
            result = {}
            
            # Processa de acordo com o tipo de evento
            if notification.event == 'PAYMENT_CONFIRMED':
                result = self._process_payment_confirmed(notification)
            elif notification.event == 'PAYMENT_RECEIVED':
                result = self._process_payment_received(notification)
            elif notification.event == 'PAYMENT_REFUNDED':
                result = self._process_payment_refunded(notification)
            elif notification.event == 'PAYMENT_DELETED':
                result = self._process_payment_deleted(notification)
            elif notification.event == 'PAYMENT_OVERDUE':
                result = self._process_payment_overdue(notification)
            elif notification.event == 'PAYMENT_CREATED':
                result = self._process_payment_created(notification)
            else:
                # Eventos que não exigem ação (visualização, etc)
                result = {
                    'success': True,
                    'message': f'Evento {notification.event} registrado mas sem ação necessária',
                    'event': notification.event
                }
            
            # Marca como processado
            notification.mark_as_processed()
            self.notification_repository.update(notification)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Erro ao processar notificação: {str(e)}',
                'error': str(e)
            }
    
    def _process_payment_confirmed(self, notification: WebhookNotification) -> Dict[str, Any]:
        """Processa pagamento confirmado"""
        # Busca Payment com estratégia em cascata
        payment = None
        
        # 1. Busca por external_reference
        if notification.external_reference:
            payment = self._get_payment_by_reference(notification.external_reference)
        
        # 2. Busca por asaas_id (payment.id do Asaas)
        if not payment and notification.payment_id:
            payment = self._get_payment_by_asaas_id(notification.payment_id)
        
        # 3. Busca por checkout_session (ID do checkout no Asaas)
        if not payment and notification.checkout_session:
            payment = self._get_payment_by_checkout_session(notification.checkout_session)
        
        # 4. Busca por installment_id - para parcelamento
        if not payment and notification.installment_id:
            payments_by_installment = self.payment_repository.get_by_installment_id(notification.installment_id)
            if payments_by_installment:
                # Pega o primeiro payment do parcelamento
                payment = payments_by_installment[0]
        
        result = {
            'success': False,
            'message': 'Nenhum pagamento ou pedido encontrado'
        }
        
        if payment:
            
            # IMPORTANTE: Atualiza o payment_id do Asaas para permitir estorno
            # O webhook envia o payment_id correto (pay_xxxxx)
            if notification.payment_id and notification.payment_id.startswith('pay_'):
                payment.asaas_id = notification.payment_id
            
            # Atualiza o método de pagamento com base no billingType da notificação
            if notification.billing_type:
                # Converte o billingType do Asaas para nosso formato
                billing_type_mapping = {
                    'CREDIT_CARD': 'CREDIT_CARD',
                    'PIX': 'PIX',
                    'BOLETO': 'BOLETO',
                    'DEBIT_CARD': 'DEBIT_CARD'
                }
                payment_method = billing_type_mapping.get(notification.billing_type, notification.billing_type)
                payment.payment_method = payment_method
            
            # Se for parcelamento, salva installment_id e installment_number
            if notification.installment_id:
                payment.installment_id = notification.installment_id
                
                # Extrai o número da parcela e o total de parcelas da descrição (ex: "Parcela 3 de 3.")
                if notification.description:
                    # Tenta extrair o número da parcela da descrição
                    match = re.search(r'Parcela\s+(\d+)\s+de\s+(\d+)', notification.description)
                    if match:
                        payment.installment_number = int(match.group(1))
                        # Atualiza o número total de parcelas
                        total_installments = int(match.group(2))
                        payment.installments = total_installments
                
                # Se não encontrou na descrição, tenta extrair do data
                if not payment.installment_number and notification.data and isinstance(notification.data, dict):
                    payment_data = notification.data.get('payment', {})
                    if payment_data:
                        # Tenta pegar o installmentNumber direto
                        installment_number = payment_data.get('installmentNumber')
                        if installment_number is not None:
                            payment.installment_number = installment_number
                        else:
                            # Tenta no formato antigo
                            installment_info = payment_data.get('installment', {})
                            if isinstance(installment_info, dict):
                                payment.installment_number = installment_info.get('sequence')
            
            payment.mark_as_paid()
            updated_payment = self.payment_repository.save(payment)
            result = {
                'success': True,
                'message': 'Pagamento confirmado',
                'payment_id': updated_payment.id,
                'asaas_payment_id': updated_payment.asaas_id,
                'status': updated_payment.status,
                'order_id': updated_payment.order_id
            }
            
            # Se houver pedido associado, atualiza status
            if payment.order_id:
                order = self.order_repository.get_by_id(payment.order_id)
                if order:
                    if order.is_pending():
                        order.confirm()
                        self.order_repository.update(order)
                        
                        # Envia email imediatamente
                        self._send_order_confirmed_email(order)
                    
                    result['order_status'] = order.status
        
        return result
    
    def _get_payment_by_checkout_session(self, checkout_session: str) -> Optional[Payment]:
        """Busca pagamento pelo checkout_session (asaas_checkout_id)"""
        if not checkout_session:
            return None
        
        try:
            return self.payment_repository.get_by_asaas_checkout_id(checkout_session)
        except:
            return None
    
    def _process_payment_received(self, notification: WebhookNotification) -> Dict[str, Any]:
        """Processa pagamento recebido (PIX)"""
        # Busca Payment com estratégia em cascata
        payment = None
        
        # 1. Busca por external_reference
        if notification.external_reference:
            payment = self._get_payment_by_reference(notification.external_reference)
        
        # 2. Busca por asaas_id (payment.id do Asaas)
        if not payment and notification.payment_id:
            payment = self._get_payment_by_asaas_id(notification.payment_id)
        
        # 3. Busca por checkout_session (ID do checkout no Asaas)
        if not payment and notification.checkout_session:
            payment = self._get_payment_by_checkout_session(notification.checkout_session)
        
        # 4. Busca por installment_id - para parcelamento
        if not payment and notification.installment_id:
            payments_by_installment = self.payment_repository.get_by_installment_id(notification.installment_id)
            if payments_by_installment:
                # Pega o primeiro payment do parcelamento
                payment = payments_by_installment[0]
        
        result = {
            'success': False,
            'message': 'Nenhum pagamento encontrado'
        }
        
        # Se não encontrou nenhum payment E tem installment_id, é uma nova parcela e precisa buscar o client e order
        if not payment and notification.installment_id and notification.customer_id:
            # Busca o cliente pelo customer_id do Asaas
            try:
                from modules.cliente.adapters.persistence.client_repository_django import ClientRepository
                client_repo = ClientRepository()
                client = client_repo.get_by_asaas_id(notification.customer_id)
                
                if client:
                    # Pega todos os payments deste installment_id para pegar info do primeiro
                    existing_payments = self.payment_repository.get_by_installment_id(notification.installment_id)
                    if existing_payments:
                        first_payment = existing_payments[0]
                        # Cria novo payment para esta parcela
                        billing_type_mapping = {
                            'CREDIT_CARD': 'CREDIT_CARD',
                            'PIX': 'PIX',
                            'BOLETO': 'BOLETO',
                            'DEBIT_CARD': 'DEBIT_CARD'
                        }
                        payment_method = billing_type_mapping.get(notification.billing_type, 'CREDIT_CARD')
                        
                        new_payment = Payment(
                            id=str(uuid4()),
                            client=client,
                            value=notification.value or Decimal('0'),
                            payment_method=payment_method,
                            order_id=first_payment.order_id if first_payment.order_id else None,
                            asaas_id=notification.payment_id,
                            asaas_checkout_id=first_payment.asaas_checkout_id,
                            status='PENDING',
                            description=notification.description or '',
                            checkout_url=first_payment.checkout_url,
                            payment_url=None,
                            external_reference=first_payment.external_reference,
                            installments=first_payment.installments,
                            installment_id=notification.installment_id,
                            installment_number=None,
                            expires_at=first_payment.expires_at,
                            created_at=datetime.now(timezone.utc)
                        )
                        
                        # Extrai installment_number e total de parcelas da descrição
                        if notification.description:
                            match = re.search(r'Parcela\s+(\d+)\s+de\s+(\d+)', notification.description)
                            if match:
                                new_payment.installment_number = int(match.group(1))
                                total_installments = int(match.group(2))
                                new_payment.installments = total_installments
                        
                        payment = self.payment_repository.save(new_payment)
            except Exception as e:
                print(f"[DEBUG] Erro ao criar payment para parcela: {str(e)}")
        
        # IMPORTANTE: Se encontrou um payment pelo checkout_session mas o asaas_id é diferente, é uma nova parcela
        # Precisamos verificar se já existe um payment com o asaas_id da notificação
        if payment and notification.payment_id:
            payment_with_asaas_id = self._get_payment_by_asaas_id(notification.payment_id)
            if payment_with_asaas_id and payment_with_asaas_id.id != payment.id:
                # Já existe um payment com este asaas_id, usa ele
                payment = payment_with_asaas_id
            elif not payment_with_asaas_id and payment.asaas_id != notification.payment_id:
                # Não existe payment com este asaas_id
                # Criar um novo payment para esta parcela
                # IMPORTANTE: description DEVE vir da notificação, não do payment antigo
                if not notification.description:
                    result['error'] = 'Notificação sem descrição'
                    return result
                
                # Converte o billingType do Asaas para nosso formato
                billing_type_mapping = {
                    'CREDIT_CARD': 'CREDIT_CARD',
                    'PIX': 'PIX',
                    'BOLETO': 'BOLETO',
                    'DEBIT_CARD': 'DEBIT_CARD'
                }
                payment_method = billing_type_mapping.get(notification.billing_type, notification.billing_type if notification.billing_type else payment.payment_method)
                
                new_payment = Payment(
                    id=str(uuid4()),
                    client=payment.client,
                    value=notification.value or payment.value,
                    payment_method=payment_method,  # Usa o billingType da notificação
                    order_id=payment.order_id,
                    asaas_id=notification.payment_id,
                    asaas_checkout_id=payment.asaas_checkout_id,
                    status='PENDING',
                    description=notification.description,  # SEMPRE usa da notificação
                    checkout_url=payment.checkout_url,
                    payment_url=None,
                    external_reference=payment.external_reference,
                    installments=payment.installments,
                    installment_id=notification.installment_id or payment.installment_id,
                    installment_number=None,  # Será extraído da descrição
                    expires_at=payment.expires_at,
                    created_at=datetime.now(timezone.utc)
                )
                # Extrai installment_number e total de parcelas da descrição
                match = re.search(r'Parcela\s+(\d+)\s+de\s+(\d+)', notification.description)
                if match:
                    new_payment.installment_number = int(match.group(1))
                    # Atualiza o número total de parcelas
                    total_installments = int(match.group(2))
                    new_payment.installments = total_installments
                
                payment = self.payment_repository.save(new_payment)
        
        if payment:
            
            # Atualiza o payment_id do Asaas se fornecido e for diferente
            if notification.payment_id and notification.payment_id.startswith('pay_') and payment.asaas_id != notification.payment_id:
                payment.asaas_id = notification.payment_id
            
            # Atualiza o método de pagamento com base no billingType da notificação
            if notification.billing_type:
                # Converte o billingType do Asaas para nosso formato
                billing_type_mapping = {
                    'CREDIT_CARD': 'CREDIT_CARD',
                    'PIX': 'PIX',
                    'BOLETO': 'BOLETO',
                    'DEBIT_CARD': 'DEBIT_CARD'
                }
                payment_method = billing_type_mapping.get(notification.billing_type, notification.billing_type)
                payment.payment_method = payment_method
            
            # IMPORTANTE: Atualiza descrição ANTES de salvar
            # Isso garante que a descrição correta seja usada na contagem de parcelas
            if notification.description:
                payment.description = notification.description
            
            # Se for parcelamento, salva installment_id e installment_number
            if notification.installment_id:
                payment.installment_id = notification.installment_id
                
                # Extrai o número da parcela e o total de parcelas da descrição (ex: "Parcela 3 de 3.")
                if notification.description:
                    # Tenta extrair o número da parcela da descrição
                    match = re.search(r'Parcela\s+(\d+)\s+de\s+(\d+)', notification.description)
                    if match:
                        payment.installment_number = int(match.group(1))
                        # Atualiza o número total de parcelas
                        total_installments = int(match.group(2))
                        payment.installments = total_installments
                
                # Se não encontrou na descrição, tenta extrair do data
                if not payment.installment_number and notification.data and isinstance(notification.data, dict):
                    payment_data = notification.data.get('payment', {})
                    if payment_data:
                        # Tenta pegar o installmentNumber direto
                        installment_number = payment_data.get('installmentNumber')
                        if installment_number is not None:
                            payment.installment_number = installment_number
                        else:
                            # Tenta no formato antigo
                            installment_info = payment_data.get('installment', {})
                            if isinstance(installment_info, dict):
                                payment.installment_number = installment_info.get('sequence')
            
            # Marca como recebido e SALVA PRIMEIRO para garantir que a descrição seja atualizada
            payment.mark_as_received()
            updated_payment = self.payment_repository.save(payment)
            
            # Variáveis para o resultado
            is_installment_payment = False
            installment_number = None
            
            # Se houver pedido associado, verifica se deve mudar para PAID
            # PAYMENT_RECEIVED: só muda para PAID se for última parcela de parcelamento
            if payment.order_id:
                order = self.order_repository.get_by_id(payment.order_id)
                if order:
                    
                    # Verifica se é pagamento parcelado (cartão em várias vezes)
                    is_installment_payment = notification.installment_id is not None
                    
                    if is_installment_payment:
                        # É parcelamento: verifica se é a última parcela
                        installment_number = self._extract_installment_number(notification)
                        
                        # IMPORTANTE: Extrai o total de parcelas APENAS da descrição da notificação ATUAL
                        # Não usa fallback no banco pois pode ter payments de teste antigos
                        total_installments = self._get_total_installments_from_description(notification.description)
                        
                        if total_installments:
                            # Conta quantas parcelas foram pagas
                            # IMPORTANTE: A função conta payments já salvos no banco, mas precisamos contar 
                            # manualmente o payment atual que acabou de ser salvo
                            paid_count = self._count_paid_installments_by_order(order.id, payment.installment_id)
                            
                            # Recarrega todos os payments novamente após o save para ter o número correto
                            all_payments = self.payment_repository.get_by_order(order.id)
                            
                            # Re-conta manualmente para garantir que estamos contando corretamente
                            actual_paid_count = 0
                            for pay in all_payments:
                                if pay.installment_id == payment.installment_id:
                                    if pay.status in ['PAID', 'RECEIVED']:
                                        if pay.description and re.search(r'Parcela\s+\d+\s+de\s+\d+', pay.description):
                                            actual_paid_count += 1
                            
                            # IMPORTANTE: Verificamos se actual_paid_count >= total_installments
                            # Isso significa que TODAS as parcelas foram recebidas
                            if actual_paid_count >= total_installments:
                                # Todas as parcelas foram recebidas: muda para PAID
                                if order.status != 'PAID':
                                    order.mark_as_paid()
                                    self.order_repository.update(order)
                                    order_status_updated = True
                                    
                                    # Envia email imediatamente
                                    self._send_order_confirmed_email(order)
                        else:
                            # Se não conseguiu determinar total de parcelas, pelo menos confirma
                            if order.is_pending():
                                order.confirm()
                                self.order_repository.update(order)
                    else:
                        # Pagamento à vista (PIX): muda para PAID quando recebido
                        if order.status != 'PAID':
                            order.mark_as_paid()
                            self.order_repository.update(order)
                            order_status_updated = True
                            
                            # Envia email imediatamente
                            self._send_order_confirmed_email(order)
            
            # Recarrega o pedido para pegar o status atualizado
            final_order_status = None
            if payment.order_id:
                final_order = self.order_repository.get_by_id(payment.order_id)
                if final_order:
                    final_order_status = final_order.status
            
            result = {
                'success': True,
                'message': 'Pagamento recebido',
                'payment_id': updated_payment.id,
                'asaas_payment_id': updated_payment.asaas_id,
                'status': updated_payment.status,
                'order_id': payment.order_id,
                'order_status': final_order_status
            }
            
            if is_installment_payment and installment_number:
                result['installment_number'] = installment_number
        
        return result
    
    def _process_payment_refunded(self, notification: WebhookNotification) -> Dict[str, Any]:
        """Processa estorno de pagamento"""
        # Busca Payment com estratégia em cascata
        payment = None
        
        if notification.external_reference:
            payment = self._get_payment_by_reference(notification.external_reference)
        
        if not payment and notification.payment_id:
            payment = self._get_payment_by_asaas_id(notification.payment_id)
        
        if not payment and notification.checkout_session:
            payment = self._get_payment_by_checkout_session(notification.checkout_session)
        
        result = {
            'success': False,
            'message': 'Nenhum pagamento encontrado'
        }
        
        if payment:
            payment.mark_as_refunded()
            updated_payment = self.payment_repository.save(payment)
            result = {
                'success': True,
                'message': 'Estorno processado',
                'payment_id': updated_payment.id,
                'status': updated_payment.status
            }
            
            # Se houver pedido associado, cancela o pedido
            if payment.order_id:
                order = self.order_repository.get_by_id(payment.order_id)
                if order and order.can_be_cancelled():
                    order.cancel()
                    self.order_repository.update(order)
                    result['order_status'] = order.status
        
        return result
    
    def _process_payment_created(self, notification: WebhookNotification) -> Dict[str, Any]:
        """Processa pagamento criado"""
        # PAYMENT_CREATED significa que uma cobrança foi criada no Asaas
        # Geralmente não precisa de ação, apenas registro
        payment = self._get_payment_by_reference(notification.external_reference)
        
        result = {
            'success': True,
            'message': 'Pagamento criado no Asaas',
            'event': 'PAYMENT_CREATED'
        }
        
        if payment:
            result['payment_id'] = payment.id
            result['payment_status'] = payment.status
        
        return result
    
    def _get_payment_by_reference(self, external_reference: str) -> Optional[Payment]:
        """Busca pagamento pela referência externa"""
        if not external_reference:
            return None
        
        return self.payment_repository.get_by_external_reference(external_reference)
    
    def _get_payment_by_asaas_id(self, asaas_id: str) -> Optional[Payment]:
        """Busca pagamento pelo asaas_id"""
        if not asaas_id:
            return None
        
        return self.payment_repository.get_by_asaas_id(asaas_id)
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Converte valor para datetime"""
        if not value:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                # Tenta vários formatos comuns
                from dateutil import parser
                return parser.parse(value)
            except:
                return None
        
        return None
    
    def _process_payment_deleted(self, notification: WebhookNotification) -> Dict[str, Any]:
        """Processa pagamento deletado"""
        # Busca Payment com estratégia em cascata
        payment = None
        
        if notification.external_reference:
            payment = self._get_payment_by_reference(notification.external_reference)
        
        if not payment and notification.payment_id:
            payment = self._get_payment_by_asaas_id(notification.payment_id)
        
        if not payment and notification.checkout_session:
            payment = self._get_payment_by_checkout_session(notification.checkout_session)
        
        result = {
            'success': False,
            'message': 'Nenhum pagamento encontrado'
        }
        
        if payment:
            # Marca como deletado
            payment.mark_as_failed()  # Usa failed como estado de deletado
            updated_payment = self.payment_repository.save(payment)
            
            result = {
                'success': True,
                'message': 'Pagamento deletado',
                'payment_id': updated_payment.id,
                'status': updated_payment.status
            }
            
            # Se houver pedido associado, cancela o pedido
            if payment.order_id:
                order = self.order_repository.get_by_id(payment.order_id)
                if order and order.can_be_cancelled():
                    order.cancel()
                    self.order_repository.update(order)
                    result['order_status'] = order.status
        
        return result
    
    def _process_payment_overdue(self, notification: WebhookNotification) -> Dict[str, Any]:
        """Processa pagamento vencido"""
        # Busca Payment com estratégia em cascata
        payment = None
        
        if notification.external_reference:
            payment = self._get_payment_by_reference(notification.external_reference)
        
        if not payment and notification.payment_id:
            payment = self._get_payment_by_asaas_id(notification.payment_id)
        
        if not payment and notification.checkout_session:
            payment = self._get_payment_by_checkout_session(notification.checkout_session)
        
        result = {
            'success': False,
            'message': 'Nenhum pagamento encontrado'
        }
        
        if payment:
            # Mantém como pendente mas marca como vencido
            # Você pode adicionar um campo específico para vencimento se necessário
            updated_payment = self.payment_repository.save(payment)
            
            result = {
                'success': True,
                'message': 'Pagamento vencido registrado',
                'payment_id': updated_payment.id,
                'status': updated_payment.status
            }
            
            # Se houver pedido associado, pode mudar status para "AGUARDANDO_PAGAMENTO"
            if payment.order_id:
                order = self.order_repository.get_by_id(payment.order_id)
                if order:
                    # Mantém o pedido como PENDING mas poderia mudar para um status específico
                    result['order_status'] = order.status
        
        return result
    
    def _extract_installment_number(self, notification: WebhookNotification) -> Optional[int]:
        """
        Extrai o número da parcela da notificação
        
        Args:
            notification: Notificação do webhook
            
        Returns:
            Número da parcela ou None
        """
        # Primeiro tenta extrair diretamente do payment.installmentNumber
        if notification.data and isinstance(notification.data, dict):
            payment_data = notification.data.get('payment', {})
            if payment_data:
                # Verifica se tem installmentNumber direto no payment
                installment_number = payment_data.get('installmentNumber')
                if installment_number is not None:
                    return installment_number
                
                # Tenta pegar do installment dentro do payment (formato antigo)
                installment_info = payment_data.get('installment', {})
                if isinstance(installment_info, dict):
                    sequence = installment_info.get('sequence')
                    if sequence is not None:
                        return sequence
        
        return None
    
    def _count_paid_installments_by_order(self, order_id: str, installment_id: str) -> int:
        """
        Conta quantas parcelas foram pagas de um parcelamento específico
        
        Args:
            order_id: ID do pedido
            installment_id: ID do parcelamento
            
        Returns:
            Número de parcelas pagas deste parcelamento
        """
        # Busca todos os pagamentos do pedido
        order_payments = self.payment_repository.get_by_order(order_id)
        
        if not order_payments:
            return 0
        
        # Conta quantos payments pagos existem com o mesmo installment_id
        # IMPORTANTE: Conta apenas payments com descrição válida de parcela (ex: "Parcela 1 de 2")
        # Ignora payments com descrição incorreta (ex: "Compra de teste")
        paid_count = 0
        for pay in order_payments:
            is_valid_installment = False
            if pay.description and re.search(r'Parcela\s+\d+\s+de\s+\d+', pay.description):
                is_valid_installment = True
            
            if pay.installment_id == installment_id and pay.status in ['PAID', 'RECEIVED'] and is_valid_installment:
                paid_count += 1
        
        return paid_count
    
    def _get_total_installments_from_description(self, description: str) -> Optional[int]:
        """
        Extrai o total de parcelas da descrição (ex: "Parcela 1 de 2." retorna 2)
        
        Args:
            description: Descrição do payment
            
        Returns:
            Total de parcelas ou None
        """
        if not description:
            return None
        
        match = re.search(r'Parcela\s+\d+\s+de\s+(\d+)', description)
        if match:
            return int(match.group(1))
        
        return None
    
    def _get_total_installments_for_order(self, order_id: str, installment_id: str) -> int:
        """
        Obtém o total de parcelas de um parcelamento
        
        Args:
            order_id: ID do pedido
            installment_id: ID do parcelamento (installment_id comum a todas as parcelas)
            
        Returns:
            Total de parcelas
        """
        # Tenta extrair da descrição primeiro (mais confiável)
        # Busca todos os pagamentos do pedido com o mesmo installment_id
        order_payments = self.payment_repository.get_by_order(order_id)
        
        if not order_payments:
            return 0
        
        # Tenta extrair o total da descrição do payment mais recente
        for pay in order_payments:
            if pay.installment_id == installment_id and pay.description:
                total_from_desc = self._get_total_installments_from_description(pay.description)
                if total_from_desc:
                    return total_from_desc
        
        # Fallback: Conta quantos payments existem com esse installment_id
        total_installments = 0
        for pay in order_payments:
            if pay.installment_id == installment_id:
                total_installments += 1
        
        return total_installments if total_installments > 0 else 0
    
    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Converte valor para Decimal"""
        if value is None or value == '':
            return None
        
        try:
            return Decimal(str(value))
        except:
            return None
    
    def _send_order_confirmed_email(self, order: Order) -> bool:
        """
        Envia email de notificação quando um pedido é confirmado
        
        Args:
            order: Entidade do pedido confirmado
            
        Returns:
            bool: True se o email foi enviado com sucesso
        """
        try:
            from modules.email.domain.services.email_service import EmailService
            from modules.cliente.domain.entities.client_entity import Client
            
            # Obtém o cliente do pedido
            client = order.client
            
            # Envia o email
            email_service = EmailService()
            success = email_service.send_order_confirmed_email(order, client)
            
            return success
            
        except Exception as e:
            return False

