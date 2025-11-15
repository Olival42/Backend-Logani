from typing import Optional, List
from modules.pagamento.domain.entities.payment_entity import Payment
from modules.pagamento.adapters.persistence.models import Payment as PaymentModel
from modules.pagamento.domain.repositories.payment_repository import IPaymentRepository
from modules.cliente.adapters.persistence.models import Client as ClientModel
from modules.cliente.adapters.persistence.client_repository_django import ClientRepository
from modules.pedido.adapters.persistence.models import Order as OrderModel


class PaymentRepository(IPaymentRepository):
    """Repositório Django para pagamentos"""
    
    def __init__(self):
        self.client_repository = ClientRepository()
    
    def save(self, payment: Payment) -> Payment:
        """Salva um pagamento"""
        # Busca cliente
        client_model = ClientModel.objects.get(id=payment.client.id)
        
        # Busca order se order_id foi fornecido
        order_model = None
        if payment.order_id:
            try:
                order_model = OrderModel.objects.get(id=payment.order_id)
            except OrderModel.DoesNotExist:
                pass
        
        # Verifica se o pagamento já existe
        try:
            payment_model = PaymentModel.objects.get(id=payment.id)
            # Atualiza campos existentes
            payment_model.client = client_model
            # Atualiza order SE foi fornecido, senão mantém o existente
            if order_model:
                payment_model.order = order_model
            payment_model.value = payment.value
            payment_model.payment_method = payment.payment_method
            # Se asaas_id foi passado, atualiza (permite sobrescrever)
            if payment.asaas_id:
                payment_model.asaas_id = payment.asaas_id
            payment_model.asaas_checkout_id = payment.asaas_checkout_id or payment_model.asaas_checkout_id
            payment_model.status = payment.status
            payment_model.description = payment.description
            payment_model.checkout_url = payment.checkout_url
            payment_model.payment_url = payment.payment_url
            payment_model.external_reference = payment.external_reference or payment_model.external_reference
            payment_model.installments = payment.installments
            payment_model.installment_id = payment.installment_id or payment_model.installment_id
            payment_model.installment_number = payment.installment_number if payment.installment_number is not None else payment_model.installment_number
            payment_model.expires_at = payment.expires_at
            payment_model.paid_at = payment.paid_at
            payment_model.refunded_at = payment.refunded_at
            payment_model.save()
        except PaymentModel.DoesNotExist:
            # Cria novo modelo de pagamento
            payment_model = PaymentModel.objects.create(
                id=payment.id,
                client=client_model,
                order=order_model if order_model else None,
                value=payment.value,
                payment_method=payment.payment_method,
                asaas_id=payment.asaas_id,
                asaas_checkout_id=payment.asaas_checkout_id,
                status=payment.status,
                description=payment.description,
                checkout_url=payment.checkout_url,
                payment_url=payment.payment_url,
                external_reference=payment.external_reference,
                installments=payment.installments,
                installment_id=payment.installment_id,
                installment_number=payment.installment_number,
                expires_at=payment.expires_at,
                paid_at=payment.paid_at,
                refunded_at=payment.refunded_at
            )
        
        payment.id = str(payment_model.id)
        return payment
    
    def get_by_id(self, payment_id: str) -> Optional[Payment]:
        """Busca um pagamento por ID"""
        try:
            payment_model = PaymentModel.objects.get(id=payment_id)
            return self._model_to_entity(payment_model)
        except PaymentModel.DoesNotExist:
            return None
    
    def get_by_client(self, client_id: str) -> List[Payment]:
        """Busca pagamentos de um cliente"""
        payment_models = PaymentModel.objects.filter(client_id=client_id)
        return [self._model_to_entity(model) for model in payment_models]
    
    def get_by_asaas_id(self, asaas_id: str) -> Optional[Payment]:
        """Busca um pagamento por asaas_id"""
        try:
            payment_model = PaymentModel.objects.get(asaas_id=asaas_id)
            return self._model_to_entity(payment_model)
        except PaymentModel.DoesNotExist:
            return None
    
    def get_by_asaas_checkout_id(self, asaas_checkout_id: str) -> Optional[Payment]:
        """Busca um pagamento por asaas_checkout_id"""
        try:
            payment_model = PaymentModel.objects.get(asaas_checkout_id=asaas_checkout_id)
            return self._model_to_entity(payment_model)
        except PaymentModel.DoesNotExist:
            return None
    
    def get_by_external_reference(self, external_reference: str) -> Optional[Payment]:
        """Busca um pagamento por referência externa"""
        try:
            payment_model = PaymentModel.objects.get(external_reference=external_reference)
            return self._model_to_entity(payment_model)
        except PaymentModel.DoesNotExist:
            return None
    
    def get_by_status(self, status: str) -> List[Payment]:
        """Busca pagamentos por status"""
        payment_models = PaymentModel.objects.filter(status=status)
        return [self._model_to_entity(model) for model in payment_models]
    
    def get_by_order(self, order_id: str) -> List[Payment]:
        """Busca pagamentos de um pedido"""
        payment_models = PaymentModel.objects.filter(order_id=order_id)
        return [self._model_to_entity(model) for model in payment_models]
    
    def get_by_installment_id(self, installment_id: str) -> List[Payment]:
        """Busca pagamentos por installment_id"""
        payment_models = PaymentModel.objects.filter(installment_id=installment_id)
        return [self._model_to_entity(model) for model in payment_models]
    
    def update(self, payment: Payment) -> Payment:
        """Atualiza um pagamento"""
        payment_model = PaymentModel.objects.get(id=payment.id)
        
        payment_model.status = payment.status
        payment_model.payment_method = payment.payment_method
        payment_model.checkout_url = payment.checkout_url
        payment_model.payment_url = payment.payment_url
        payment_model.paid_at = payment.paid_at
        payment_model.refunded_at = payment.refunded_at
        # Atualiza asaas_id se fornecido (importante para webhook)
        if payment.asaas_id:
            payment_model.asaas_id = payment.asaas_id
        
        payment_model.save()
        return payment
    
    def list_all(self) -> List[Payment]:
        """Lista todos os pagamentos"""
        payment_models = PaymentModel.objects.all()
        return [self._model_to_entity(model) for model in payment_models]
    
    def _model_to_entity(self, model: PaymentModel) -> Payment:
        """Converte modelo Django para entidade"""
        from modules.cliente.domain.entities.client_entity import Client as ClientEntity
        from modules.cliente.domain.entities.address_entity import Address as AddressEntity
        
        # Converte cliente
        client_model = model.client
        address_model = client_model.address if hasattr(client_model, 'address') else None
        
        address_entity = None
        if address_model:
            address_entity = AddressEntity(
                address=address_model.address,
                number=address_model.address_number,
                postal_code=address_model.postal_code,
                city=address_model.city,
                state=address_model.state,
                complement=address_model.complement or '',
                province=address_model.province
            )
        
        user_model = getattr(client_model, 'user', None)
        client_entity = ClientEntity(
            id=str(client_model.id),
            name=client_model.name,
            cpf=client_model.cpf,
            phone=client_model.phone or '',
            mobile_phone=client_model.mobile_phone or '',
            address=address_entity or AddressEntity('', '', '', '', '', '', ''),
            user=user_model,
            asaas_id=client_model.asaas_id,
            email=user_model.email if user_model and getattr(user_model, 'email', None) else None
        )
        
        return Payment(
            id=str(model.id),
            client=client_entity,
            value=model.value,
            payment_method=model.payment_method,
            order_id=str(model.order_id) if model.order else None,
            asaas_id=model.asaas_id,
            asaas_checkout_id=model.asaas_checkout_id,
            status=model.status,
            description=model.description,
            checkout_url=model.checkout_url,
            payment_url=model.payment_url,
            external_reference=model.external_reference,
            installments=model.installments,
            expires_at=model.expires_at,
            paid_at=model.paid_at,
            refunded_at=model.refunded_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            installment_id=model.installment_id,
            installment_number=model.installment_number
        )

