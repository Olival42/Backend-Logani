from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from uuid import uuid4
from django.db import transaction
import time
import logging

from modules.checkout.domain.entities.checkout_entity import Checkout
from modules.checkout.domain.repositories.checkout_repository import ICheckoutRepository
from modules.checkout.adapters.external.asaas_checkout_client import AsaasCheckoutClient
from modules.cliente.domain.entities.client_entity import Client as ClientEntity
from modules.cliente.adapters.persistence.client_repository_django import ClientRepository
from modules.pagamento.domain.entities.payment_entity import Payment as PaymentEntity
from modules.pedido.domain.repositories.order_repository import IOrderRepository

logger = logging.getLogger(__name__)


class CheckoutService:
    """
    ⚠️ DEPRECATED: Use PaymentService para novos fluxos
    
    Este serviço foi mantido para compatibilidade com sistemas legados.
    Para novos desenvolvimentos, use o módulo PAGAMENTO.
    
    Responsabilidade recomendada do CHECKOUT:
    - ✅ Criar link de pagamento no Asaas
    - ✅ Retornar URL para cliente acessar
    - ❌ NÃO gerencia estornos (use PaymentService)
    - ❌ NÃO gerencia webhooks (use WebhookNotificationService)
    - ❌ NÃO vincula com pedidos (use PaymentService)
    
    Serviço de domínio para gerenciamento de checkouts (legacy)
    """
    
    def __init__(self, checkout_repository: ICheckoutRepository):
        self.checkout_repository = checkout_repository
        self.asaas_client = AsaasCheckoutClient()
        self.client_repository = ClientRepository()
        
        # Inicializa o repositório de pagamentos se disponível
        try:
            from modules.pagamento.adapters.persistence.payment_repository_django import PaymentRepository
            from modules.pedido.adapters.persistence.order_repository_django import OrderRepository
            self.payment_repository = PaymentRepository()
            self.order_repository = OrderRepository()
        except:
            self.payment_repository = None
            self.order_repository = None
    
    def create_checkout(
        self,
        value: Decimal,
        customer: str,
        chargeTypes: List[str],
        minutesToExpire: int,
        description: Optional[str] = None,
        externalReference: Optional[str] = None,
        successUrl: Optional[str] = None,
        failureUrl: Optional[str] = None,
        expiresUrl: Optional[str] = None,
        installments: int = 1,
        paymentMethods: Optional[List[str]] = None,
        items: Optional[List[Dict]] = None,
        installment: Optional[Dict] = None,
        order_id: Optional[str] = None  # Otimização: evita busca duplicada do pedido
    ) -> Dict[str, Any]:
        """
        Cria um novo checkout baseado na documentação ASAAS
        
        Args:
            value: Valor do checkout
            customer: ID do cliente no ASAAS (formato: cus_xxxxx)
            chargeTypes: Tipos de cobrança (DETACHED, RECURRENT, INSTALLMENT)
            minutesToExpire: Minutos para expiração do checkout
            description: Descrição do checkout
            externalReference: Referência externa
            successUrl: URL de sucesso
            failureUrl: URL de falha
            expiresUrl: URL de expiração
            installments: Número de parcelas
            paymentMethods: Métodos de pagamento aceitos
            items: Lista de itens do checkout
            
        Returns:
            Dict com informações do checkout criado
            
        Raises:
            ValueError: Em caso de erro na criação
        """
        try:
            # Obtém o walletId do .env
            import os
            walletId = os.getenv('ASAAS_WALLET_ID')
            if not walletId:
                raise ValueError("WalletId não encontrado nas variáveis de ambiente (ASAAS_WALLET_ID)")
            
            # Busca o cliente local pelo asaas_id
            client_start = time.time()
            client_entity = self.client_repository.get_by_asaas_id(customer)
            if not client_entity:
                raise ValueError(f"Cliente com ID ASAAS '{customer}' não encontrado no sistema local")
            logger.info(f"⏱️ [Service] Busca cliente: {(time.time() - client_start)*1000:.2f}ms")
            
            # Calcula data de expiração baseada nos minutos (usa timezone do Django)
            from django.utils import timezone
            expires_at = timezone.now() + timedelta(minutes=minutesToExpire)
            
            # Gera nome baseado no tipo de cobrança e cliente
            name = f"Checkout {chargeTypes[0]} - {client_entity.name}"
            
            # Cria a entidade checkout
            checkout = Checkout(
                id=None,  # Será gerado pelo repositório
                name=name,
                value=value,
                client=client_entity,
                installments=installments,
                description=description,
                success_url=successUrl,
                failure_url=failureUrl,
                expires_url=expiresUrl,
                external_reference=externalReference,
                expires_at=expires_at
            )
            
            # Cria primeiro no Asaas
            asaas_start = time.time()
            asaas_response = self.asaas_client.create_checkout(
                checkout=checkout,
                items=items,
                walletId=walletId,
                paymentMethods=paymentMethods,
                minutesToExpire=minutesToExpire,
                chargeTypes=chargeTypes,
                installment=installment
            )
            logger.info(f"⏱️ [Service] Chamada Asaas (total): {(time.time() - asaas_start)*1000:.2f}ms")
            
            if 'id' not in asaas_response:
                raise ValueError("Asaas não retornou ID do checkout criado")
            
            # Atualiza a entidade com os dados do Asaas
            # O ID do checkout no Asaas é retornado como 'checkoutSession' ou 'id'
            asaas_checkout_id = asaas_response.get('checkoutSession') or asaas_response.get('id')
            # O Asaas retorna 'link' como URL do checkout
            checkout_url = asaas_response.get('link', '')
            
            checkout.set_asaas_data(
                asaas_id=asaas_checkout_id,
                checkout_url=checkout_url
            )
            
            # Guarda o ID do checkout no Asaas para possível rollback
            asaas_checkout_id_for_rollback = asaas_checkout_id
            
            # Salva no repositório local com transação atômica
            # Se falhar, tenta fazer rollback no Asaas
            db_start = time.time()
            try:
                with transaction.atomic():
                    saved_checkout = self.checkout_repository.save(checkout)
                    logger.info(f"⏱️ [Service] Save checkout: {(time.time() - db_start)*1000:.2f}ms")
                    
                    # Cria Payment associado ao Checkout dentro da mesma transação
                    payment = None
                    order_id = None
                    
                    # Tenta encontrar o pedido pelo external_reference se existir
                    if externalReference and self.order_repository:
                        try:
                            order = self.order_repository.get_by_external_reference(externalReference)
                            if order:
                                # Verifica se o pedido está ativo
                                if not order.active:
                                    raise ValueError("Não é possível criar checkout para um pedido inativo")
                                order_id = order.id
                        except ValueError:
                            raise  # Re-lança ValueError (erro de pedido inativo)
                        except:
                            pass  # Ignora outros erros (pedido não encontrado, etc)
                    
                    # Cria o Payment se o repositório estiver disponível
                    if self.payment_repository:
                        try:
                            payment = PaymentEntity(
                                id=str(uuid4()),
                                client=client_entity,
                                value=value,
                                payment_method=paymentMethods[0] if paymentMethods else 'UNKNOWN',
                                order_id=order_id,
                                asaas_checkout_id=saved_checkout.asaas_id,  # ID do checkout no Asaas
                                status='PENDING',
                                description=description,
                                checkout_url=saved_checkout.checkout_url,
                                external_reference=externalReference,
                                installments=installments,
                                expires_at=expires_at,
                                created_at=timezone.now()
                            )
                            payment = self.payment_repository.save(payment)
                        except Exception as e:
                            # Se falhar ao criar payment, cancela toda a transação
                            raise ValueError(f"Erro ao criar payment associado ao checkout: {str(e)}")
            except Exception as db_error:
                # Se falhar ao salvar no banco, tenta cancelar o checkout no Asaas
                if asaas_checkout_id_for_rollback:
                    try:
                        self.asaas_client.cancel_checkout(asaas_checkout_id_for_rollback)
                    except Exception as rollback_error:
                        # Se falhar o rollback, agenda limpeza assíncrona
                        print(f"❌ Erro ao cancelar checkout no Asaas: {rollback_error}")
                        try:
                            from modules.pagamento.tasks import cleanup_orphaned_checkouts_async
                            # Agenda limpeza assíncrona para tentar novamente depois
                            cleanup_orphaned_checkouts_async.delay([asaas_checkout_id_for_rollback])
                        except Exception as task_error:
                            print(f"⚠️ Erro ao agendar task de limpeza: {task_error}")
                
                # Propaga o erro original do banco
                if isinstance(db_error, ValueError):
                    raise db_error
                raise ValueError(f"Erro ao salvar checkout no banco de dados: {str(db_error)}")
            
            # Prepara os dados do cliente para a resposta
            client_data = {
                'id': str(client_entity.id),
                'name': client_entity.name,
                'cpf': client_entity.cpf,
                'phone': client_entity.phone,
                'mobile_phone': client_entity.mobile_phone,
                'email': client_entity.user.email if client_entity.user else None,
                'asaas_id': client_entity.asaas_id
            }
            
            # Adiciona os dados do cliente na resposta do Asaas
            asaas_response_with_client = asaas_response.copy()
            asaas_response_with_client['customerData'] = client_data
            
            return {
                'local_id': str(saved_checkout.id),
                'asaas_id': saved_checkout.asaas_id,
                'checkout_url': saved_checkout.checkout_url,
                'name': saved_checkout.name,
                'value': float(saved_checkout.value),
                'status': saved_checkout.status,
                'expires_at': saved_checkout.expires_at.isoformat() if saved_checkout.expires_at else None,
                'payment_id': str(payment.id) if payment else None,
                'asaas_response': asaas_response_with_client
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao criar checkout: {str(e)}")
    
    def get_checkout(self, checkout_id: str) -> Optional[Checkout]:
        """
        Busca um checkout por ID
        
        Args:
            checkout_id: ID do checkout
            
        Returns:
            Entidade Checkout ou None se não encontrado
        """
        return self.checkout_repository.get_by_id(checkout_id)
    
    def get_checkout_by_asaas_id(self, asaas_id: str) -> Optional[Checkout]:
        """
        Busca um checkout por ID do ASAAS
        
        Args:
            asaas_id: ID do checkout no ASAAS
            
        Returns:
            Entidade Checkout ou None se não encontrado
        """
        return self.checkout_repository.get_by_asaas_id(asaas_id)
    
    def get_client_checkouts(self, client_id: str) -> List[Checkout]:
        """
        Busca checkouts de um cliente
        
        Args:
            client_id: ID do cliente
            
        Returns:
            Lista de checkouts do cliente
        """
        return self.checkout_repository.get_by_client(client_id)
    
    def cancel_checkout(self, checkout_id: str) -> Dict[str, Any]:
        """
        Cancela um checkout
        
        Args:
            checkout_id: ID do checkout
            
        Returns:
            Dict com informações do cancelamento
            
        Raises:
            ValueError: Em caso de erro no cancelamento
        """
        try:
            # Busca o checkout
            checkout = self.checkout_repository.get_by_id(checkout_id)
            if not checkout:
                raise ValueError("Checkout não encontrado")
            
            # Verifica se pode ser cancelado
            if not checkout.can_be_cancelled():
                raise ValueError("Checkout não pode ser cancelado")
            
            # Guarda o ID do checkout no Asaas para possível rollback
            asaas_checkout_id_for_rollback = checkout.asaas_id
            
            # Cancela no Asaas primeiro (antes da transação local)
            asaas_response = None
            asaas_cancelled = False
            if checkout.asaas_id:
                try:
                    asaas_response = self.asaas_client.cancel_checkout(checkout.asaas_id)
                    # Verifica se foi cancelado com sucesso
                    # O Asaas pode retornar o status na resposta ou precisamos consultar depois
                    if asaas_response:
                        # Tenta verificar o status na resposta
                        asaas_status = asaas_response.get('status', '')
                        if asaas_status == 'CANCELED' or asaas_response.get('deleted', False):
                            asaas_cancelled = True
                        else:
                            # Consulta o checkout para confirmar o status
                            try:
                                checkout_info = self.asaas_client.get_checkout(checkout.asaas_id)
                                asaas_status = checkout_info.get('status', '').upper()
                                if asaas_status == 'CANCELED' or asaas_status == 'CANCELLED':
                                    asaas_cancelled = True
                            except Exception as check_error:
                                print(f"⚠️ Não foi possível confirmar o cancelamento no Asaas: {check_error}")
                    else:
                        # Se não retornou dados, assume sucesso se não houve exceção
                        asaas_cancelled = True
                except Exception as asaas_error:
                    # Se falhar ao cancelar no Asaas, continua com o cancelamento local
                    print(f"⚠️ Erro ao cancelar checkout no Asaas: {asaas_error}")
            
            # Cancela localmente com transação atômica
            try:
                with transaction.atomic():
                    checkout.cancel()
                    self.checkout_repository.save(checkout)
                    
                    # Cancela o Payment associado ao checkout se existir
                    if self.payment_repository and checkout.asaas_id:
                        try:
                            # Busca payment pelo asaas_checkout_id
                            payment = self.payment_repository.get_by_asaas_checkout_id(checkout.asaas_id)
                            if payment and payment.can_be_cancelled():
                                payment.cancel()
                                self.payment_repository.save(payment)
                        except Exception as payment_error:
                            # Se falhar ao cancelar payment, não interrompe o cancelamento do checkout
                            print(f"⚠️ Erro ao cancelar payment associado: {payment_error}")
                    
                    # Cancela o Order associado ao checkout se existir (através do external_reference)
                    if checkout.external_reference and self.order_repository:
                        try:
                            order = self.order_repository.get_by_external_reference(checkout.external_reference)
                            if order and order.can_be_cancelled():
                                order.cancel()
                                self.order_repository.update(order)
                        except Exception as order_error:
                            # Se falhar ao cancelar order, não interrompe o cancelamento do checkout
                            print(f"⚠️ Erro ao cancelar order associado: {order_error}")
                    
            except Exception as db_error:
                # Se falhar ao salvar no banco, já tentamos cancelar no Asaas acima
                # A transação atômica já faz rollback automático
                if isinstance(db_error, ValueError):
                    raise db_error
                raise ValueError(f"Erro ao salvar checkout no banco de dados: {str(db_error)}")
            
            return {
                'local_id': str(checkout.id),
                'asaas_id': checkout.asaas_id,
                'status': checkout.status,
                'asaas_cancelled': asaas_cancelled,
                'asaas_response': asaas_response
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao cancelar checkout: {str(e)}")
    
    def sync_checkout_status(self, checkout_id: str) -> Dict[str, Any]:
        """
        Sincroniza o status de um checkout com o ASAAS
        
        Args:
            checkout_id: ID do checkout
            
        Returns:
            Dict com informações da sincronização
            
        Raises:
            ValueError: Em caso de erro na sincronização
        """
        try:
            # Busca o checkout
            checkout = self.checkout_repository.get_by_id(checkout_id)
            if not checkout:
                raise ValueError("Checkout não encontrado")
            
            if not checkout.asaas_id:
                raise ValueError("Checkout não está sincronizado com o Asaas")
            
            # Busca dados atualizados no Asaas
            asaas_response = self.asaas_client.get_checkout(checkout.asaas_id)
            
            # Atualiza status se necessário
            asaas_status = asaas_response.get('status', '')
            expired_result = None
            if asaas_status == 'PAID' and checkout.status != 'PAID':
                checkout.mark_as_paid()
                self.checkout_repository.save(checkout)
            elif asaas_status == 'CHECKOUT_EXPIRED':
                expired_result = self._handle_checkout_expired(checkout)
            
            return {
                'local_id': str(checkout.id),
                'asaas_id': checkout.asaas_id,
                'local_status': checkout.status,
                'asaas_status': asaas_status,
                'asaas_data': asaas_response,
                'expired_processing': expired_result
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao sincronizar checkout: {str(e)}")
    
    def expire_checkouts(self) -> int:
        """
        Expira checkouts que passaram da data de expiração
        
        Returns:
            Número de checkouts expirados
        """
        expired_checkouts = self.get_expired_checkouts()
        count = 0
        
        for checkout in expired_checkouts:
            self._handle_checkout_expired(checkout)
            count += 1
        
        return count
    
    def handle_checkout_expired_by_asaas_id(self, asaas_id: str) -> Dict[str, Any]:
        """Processa expiração de checkout a partir do ID do Asaas."""
        checkout = self.checkout_repository.get_by_asaas_id(asaas_id)
        if not checkout:
            raise ValueError("Checkout não encontrado para o ID do Asaas fornecido.")
        return self._handle_checkout_expired(checkout)
    
    def handle_checkout_expired_by_reference(self, external_reference: str) -> Dict[str, Any]:
        """Processa expiração de checkout a partir da referência externa."""
        checkout = self.checkout_repository.get_by_external_reference(external_reference)
        if not checkout:
            raise ValueError("Checkout não encontrado para a referência externa fornecida.")
        return self._handle_checkout_expired(checkout)
    
    def _handle_checkout_expired(self, checkout: Checkout) -> Dict[str, Any]:
        """
        Processa checkout expirado:
        - Atualiza status do checkout para EXPIRED
        - Reativa pedido associado (status PENDING)
        - Cancela pagamento associado (se existir)
        """
        order_updated = False
        order_id = None
        payment_cancelled = False
        payment_id = None
        
        with transaction.atomic():
            previous_status = checkout.status
            if checkout.status == 'PENDING':
                checkout.expire()
            else:
                checkout.status = 'EXPIRED'
                checkout.updated_at = datetime.now()
            self.checkout_repository.save(checkout)
            
            external_reference = checkout.external_reference
            if external_reference and self.order_repository:
                try:
                    order = self.order_repository.get_by_external_reference(external_reference)
                    if order:
                        order_id = str(order.id)
                        if order.status != 'PENDING':
                            order.status = 'PENDING'
                            order.confirmed_at = None
                            order.updated_at = datetime.now(dt_timezone.utc)
                            self.order_repository.update(order)
                            order_updated = True
                except Exception as order_error:
                    logger.warning(f"⚠️ Erro ao atualizar pedido associado ao checkout expirado: {order_error}")
            
            if self.payment_repository:
                try:
                    payment = None
                    if checkout.asaas_id:
                        payment = self.payment_repository.get_by_asaas_checkout_id(checkout.asaas_id)
                    if not payment and external_reference:
                        payment = self.payment_repository.get_by_external_reference(external_reference)
                    if payment:
                        payment_id = payment.id
                        if payment.status not in ['CANCELLED', 'REFUNDED']:
                            if payment.status == 'PENDING':
                                payment.cancel()
                            else:
                                payment.status = 'CANCELLED'
                                payment.updated_at = datetime.now(dt_timezone.utc)
                            self.payment_repository.save(payment)
                            payment_cancelled = True
                except Exception as payment_error:
                    logger.warning(f"⚠️ Erro ao cancelar payment associado ao checkout expirado: {payment_error}")
        
        return {
            'success': True,
            'message': 'Checkout expirado processado',
            'checkout_id': str(checkout.id) if checkout.id else None,
            'checkout_status': checkout.status,
            'previous_status': previous_status,
            'order_updated': order_updated,
            'order_id': order_id,
            'payment_cancelled': payment_cancelled,
            'payment_id': payment_id
        }
    
    def get_expired_checkouts(self) -> List[Checkout]:
        """
        Busca checkouts expirados
        
        Returns:
            Lista de checkouts expirados
        """
        from django.utils import timezone
        now = timezone.now()
        
        # Busca checkouts pendentes que expiraram
        expired_checkouts = []
        pending_checkouts = self.checkout_repository.get_by_status('PENDING')
        
        for checkout in pending_checkouts:
            if checkout.expires_at and checkout.expires_at < now:
                expired_checkouts.append(checkout)
        
        return expired_checkouts
    
    def refund_checkout(self, checkout_id: str, value: Optional[Decimal] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Solicita estorno de um checkout/pagamento
        
        Args:
            checkout_id: ID do checkout local
            value: Valor a estornar (opcional, estorna tudo se não informado)
            description: Descrição do estorno (opcional)
            
        Returns:
            Dict com informações do estorno
            
        Raises:
            ValueError: Em caso de erro no estorno
        """
        try:
            # Busca o checkout
            checkout = self.checkout_repository.get_by_id(checkout_id)
            if not checkout:
                raise ValueError("Checkout não encontrado")
            
            # Verifica se pode ser estornado (deve estar PAID ou RECEIVED)
            if checkout.status not in ['PAID', 'RECEIVED']:
                raise ValueError("Apenas checkouts pagos ou recebidos podem ser estornados")
            
            # Busca o payment_id através do checkout do Asaas
            # O Asaas retorna o payment_id quando o checkout é pago
            # Mas como temos apenas o checkout_id do Asaas, precisamos buscar mais informações
            if not checkout.asaas_id:
                raise ValueError("Checkout não está sincronizado com o Asaas")
            
            # Busca dados do checkout no Asaas para obter o payment_id
            asaas_checkout_data = self.asaas_client.get_checkout(checkout.asaas_id)
            
            # O payment_id geralmente vem na resposta quando o checkout é pago
            payment_id = asaas_checkout_data.get('payment_id') or asaas_checkout_data.get('id')
            
            if not payment_id:
                raise ValueError("Não foi possível identificar o pagamento para estorno")
            
            # Solicita estorno no Asaas
            refund_value = float(value) if value else None
            asaas_response = self.asaas_client.refund_payment(
                payment_id=payment_id,
                value=refund_value,
                description=description or f"Estorno do checkout {checkout.name}"
            )
            
            # Atualiza status local para REFUNDING (estornando)
            # O status será atualizado para REFUNDED pelo webhook
            checkout.status = 'REFUNDING'
            from datetime import datetime
            checkout.updated_at = datetime.now()
            self.checkout_repository.save(checkout)
            
            return {
                'local_id': str(checkout.id),
                'asaas_id': checkout.asaas_id,
                'payment_id': payment_id,
                'status': checkout.status,
                'asaas_response': asaas_response
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao estornar checkout: {str(e)}")