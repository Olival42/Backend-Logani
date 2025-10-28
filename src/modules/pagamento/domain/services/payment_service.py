from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from modules.pagamento.domain.entities.payment_entity import Payment
from modules.pagamento.domain.repositories.payment_repository import IPaymentRepository
from modules.checkout.domain.repositories.checkout_repository import ICheckoutRepository
from modules.checkout.adapters.external.asaas_checkout_client import AsaasCheckoutClient
from modules.cliente.domain.entities.client_entity import Client as ClientEntity


class PaymentService:
    """
    Serviço de domínio para gerenciamento de pagamentos
    Integra com o módulo de checkout existente para pagamentos via Asaas
    """
    
    def __init__(self, payment_repository: IPaymentRepository):
        self.payment_repository = payment_repository
        self.asaas_client = AsaasCheckoutClient()
    
    def create_payment(
        self,
        client: ClientEntity,
        value: Decimal,
        payment_method: str,
        order_id: Optional[str] = None,
        installments: int = 1,
        description: Optional[str] = None,
        external_reference: Optional[str] = None,
        minutes_to_expire: int = 1440,
        items: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Cria um novo pagamento e checkout no Asaas
        
        Args:
            client: Entidade do cliente
            value: Valor do pagamento
            payment_method: Método de pagamento (PIX, CREDIT_CARD, BOLETO)
            order_id: ID do pedido relacionado (opcional)
            installments: Número de parcelas
            description: Descrição do pagamento
            external_reference: Referência externa
            minutes_to_expire: Minutos para expiração
            items: Lista de itens do pagamento
            
        Returns:
            Dict com informações do pagamento criado
        """
        try:
            # Valida payment_method
            valid_methods = ['PIX', 'CREDIT_CARD', 'BOLETO', 'DEBIT_CARD']
            if payment_method not in valid_methods:
                raise ValueError(f"Método de pagamento inválido. Use: {', '.join(valid_methods)}")
            
            # Obtém walletId
            import os
            wallet_id = os.getenv('ASAAS_WALLET_ID')
            if not wallet_id:
                raise ValueError("WalletId não encontrado nas variáveis de ambiente (ASAAS_WALLET_ID)")
            
            # Calcula data de expiração
            expires_at = datetime.now() + timedelta(minutes=minutes_to_expire)
            
            # Mapeia payment_method para billingTypes do Asaas
            billing_types_map = {
                'PIX': ['PIX'],
                'CREDIT_CARD': ['CREDIT_CARD'],
                'BOLETO': ['BOLETO'],
                'DEBIT_CARD': ['DEBIT_CARD']
            }
            billing_types = billing_types_map.get(payment_method, ['CREDIT_CARD', 'PIX'])
            
            # Charge types baseado no método
            charge_types = ['DETACHED']  # Cobrança única
            
            # Cria entidade de pagamento
            payment = Payment(
                id=str(uuid4()),
                client=client,
                value=value,
                payment_method=payment_method,
                order_id=order_id,
                status='PENDING',
                description=description or f"Pagamento via {payment_method}",
                external_reference=external_reference or f"PAY_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid4())[:8].upper()}",
                installments=installments,
                expires_at=expires_at
            )
            
            # Cria checkout no Asaas usando a entidade de domínio Checkout
            from modules.checkout.domain.entities.checkout_entity import Checkout
            
            temp_checkout = Checkout(
                id=str(uuid4()),
                name=f"Payment {payment_method} - {client.name}",
                value=value,
                client=client,
                installments=installments,
                description=description,
                external_reference=payment.external_reference,
                expires_at=expires_at
            )
            
            # Chama API do Asaas
            asaas_response = self.asaas_client.create_checkout(
                checkout=temp_checkout,
                items=items,
                walletId=wallet_id,
                paymentMethods=billing_types,
                minutesToExpire=minutes_to_expire,
                chargeTypes=charge_types
            )
            
            if 'id' not in asaas_response:
                raise ValueError("Asaas não retornou ID do checkout criado")
            
            # Atualiza payment com dados do Asaas
            payment.set_asaas_data(
                asaas_id=asaas_response.get('id'),
                checkout_url=asaas_response.get('checkoutUrl', '')
            )
            payment.asaas_checkout_id = asaas_response.get('id')
            
            # Salva pagamento
            saved_payment = self.payment_repository.save(payment)
            
            return {
                'payment_id': str(saved_payment.id),
                'asaas_id': saved_payment.asaas_id,
                'checkout_url': saved_payment.checkout_url,
                'value': float(saved_payment.value),
                'payment_method': saved_payment.payment_method,
                'status': saved_payment.status,
                'external_reference': saved_payment.external_reference,
                'installments': saved_payment.installments,
                'expires_at': saved_payment.expires_at.isoformat() if saved_payment.expires_at else None,
                'asaas_response': asaas_response
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao criar pagamento: {str(e)}")
    
    def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Busca um pagamento por ID"""
        return self.payment_repository.get_by_id(payment_id)
    
    def get_payment_by_reference(self, external_reference: str) -> Optional[Payment]:
        """Busca um pagamento por referência externa"""
        return self.payment_repository.get_by_external_reference(external_reference)
    
    def get_order_payments(self, order_id: str) -> List[Payment]:
        """Busca pagamentos de um pedido"""
        return self.payment_repository.get_by_order(order_id)
    
    def refund_payment(
        self, 
        payment_id: Optional[str] = None, 
        external_reference: Optional[str] = None,
        asaas_id: Optional[str] = None,
        value: Optional[Decimal] = None, 
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Solicita estorno de um pagamento
        
        Args:
            payment_id: ID do pagamento local
            external_reference: Referência externa do pagamento
            asaas_id: ID do pagamento no Asaas (opcional)
            value: Valor a estornar (opcional, estorna tudo se não informado)
            description: Descrição do estorno
            
        Returns:
            Dict com informações do estorno
        """
        try:
            # Busca o pagamento por ID ou external_reference
            payment = None
            if payment_id:
                payment = self.payment_repository.get_by_id(payment_id)
            elif external_reference:
                payment = self.payment_repository.get_by_external_reference(external_reference)
            elif asaas_id:
                payment = self.payment_repository.get_by_asaas_id(asaas_id)
            
            if not payment:
                raise ValueError("Pagamento não encontrado")
            
            # Verifica se pode ser estornado
            if not payment.can_be_refunded():
                raise ValueError(f"Apenas pagamentos pagos ou recebidos podem ser estornados. Status atual: {payment.status}")
            
            # Usa o asaas_id ou busca o payment_id do Asaas
            payment_id_asaas = asaas_id or payment.asaas_id
            
            if not payment_id_asaas:
                # Se não tiver asaas_id, busca no checkout que criou o pagamento
                # Pode precisar sincronizar com Asaas para obter o payment_id correto
                raise ValueError("Não foi possível identificar o pagamento no Asaas para estorno")
            
            # Solicita estorno no Asaas
            # IMPORTANTE: O Asaas precisa do payment_id, não do checkout_id
            # Vamos usar o asaas_id que pode ser o checkout_id
            # Mas o ideal seria ter o payment_id retornado quando o checkout é pago
            
            # Para estorno, o endpoint correto é:
            # POST /payments/{payment_id}/refund
            # Onde payment_id é o ID retornado quando o pagamento é processado
            
            # Por enquanto, tenta estornar usando o asaas_id
            # Isso funciona se o asaas_id for o payment_id correto
            refund_value = float(value) if value else None
            asaas_response = self.asaas_client.refund_payment(
                payment_id=payment_id_asaas,
                value=refund_value,
                description=description or f"Estorno do pagamento {payment.external_reference}"
            )
            
            # Atualiza status local para REFUNDING (será atualizado para REFUNDED pelo webhook)
            payment.status = 'REFUNDING'
            payment.updated_at = datetime.now()
            updated_payment = self.payment_repository.save(payment)
            
            return {
                'payment_id': str(updated_payment.id),
                'asaas_id': updated_payment.asaas_id,
                'status': updated_payment.status,
                'refund_value': float(value) if value else None,
                'description': description,
                'asaas_response': asaas_response
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao estornar pagamento: {str(e)}")
    
    def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Cancela um pagamento pendente
        
        Args:
            payment_id: ID do pagamento
            
        Returns:
            Dict com informações do cancelamento
        """
        try:
            # Busca o pagamento
            payment = self.payment_repository.get_by_id(payment_id)
            if not payment:
                raise ValueError("Pagamento não encontrado")
            
            # Verifica se pode ser cancelado
            if not payment.can_be_cancelled():
                raise ValueError("Pagamento não pode ser cancelado")
            
            # Cancela no Asaas se tiver checkout_id
            if payment.asaas_checkout_id:
                self.asaas_client.cancel_checkout(payment.asaas_checkout_id)
            
            # Cancela localmente
            payment.cancel()
            self.payment_repository.save(payment)
            
            return {
                'payment_id': str(payment.id),
                'status': payment.status
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao cancelar pagamento: {str(e)}")

