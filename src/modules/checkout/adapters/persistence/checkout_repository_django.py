from typing import List, Optional
from uuid import uuid4
from django.utils import timezone

from modules.checkout.domain.entities.checkout_entity import Checkout
from modules.checkout.domain.repositories.checkout_repository import ICheckoutRepository
from modules.checkout.adapters.persistence.models import Checkout as CheckoutModel
from modules.cliente.domain.entities.client_entity import Client as ClientEntity
from modules.cliente.adapters.persistence.models import Client as ClientModel


class CheckoutRepository(ICheckoutRepository):
    """
    Implementação do repositório de checkout usando Django ORM
    """
    
    def save(self, checkout: Checkout) -> Checkout:
        """Salva um checkout"""
        try:
            # Busca o modelo do cliente
            client_model = ClientModel.objects.get(id=checkout.client.id)
            
            # Cria ou atualiza o modelo do checkout
            checkout_model, created = CheckoutModel.objects.update_or_create(
                id=checkout.id or str(uuid4()),
                defaults={
                    'name': checkout.name,
                    'value': checkout.value,
                    'client': client_model,
                    'installments': checkout.installments,
                    'description': checkout.description,
                    'status': checkout.status,
                    'asaas_id': checkout.asaas_id,
                    'checkout_url': checkout.checkout_url,
                    'success_url': checkout.success_url,
                    'failure_url': checkout.failure_url,
                    'expires_url': checkout.expires_url,
                    'external_reference': checkout.external_reference,
                    'expires_at': checkout.expires_at,
                }
            )
            
            # Atualiza o ID da entidade se foi criada
            if created:
                checkout.id = str(checkout_model.id)
            
            return checkout
            
        except ClientModel.DoesNotExist:
            raise ValueError("Cliente não encontrado")
        except Exception as e:
            raise ValueError(f"Erro ao salvar checkout: {str(e)}")
    
    def get_by_id(self, checkout_id: str) -> Optional[Checkout]:
        """Busca um checkout por ID"""
        try:
            checkout_model = CheckoutModel.objects.get(id=checkout_id)
            return self._model_to_entity(checkout_model)
        except CheckoutModel.DoesNotExist:
            return None
    
    def get_by_asaas_id(self, asaas_id: str) -> Optional[Checkout]:
        """Busca um checkout por ID do ASAAS"""
        try:
            checkout_model = CheckoutModel.objects.get(asaas_id=asaas_id)
            return self._model_to_entity(checkout_model)
        except CheckoutModel.DoesNotExist:
            return None
    
    def get_by_external_reference(self, external_reference: str) -> Optional[Checkout]:
        """Busca um checkout pela referência externa"""
        try:
            checkout_model = CheckoutModel.objects.get(external_reference=external_reference)
            return self._model_to_entity(checkout_model)
        except CheckoutModel.DoesNotExist:
            return None
    
    def get_by_client(self, client_id: str) -> List[Checkout]:
        """Busca checkouts por cliente"""
        checkout_models = CheckoutModel.objects.filter(client_id=client_id).order_by('-created_at')
        return [self._model_to_entity(model) for model in checkout_models]
    
    def get_by_status(self, status: str) -> List[Checkout]:
        """Busca checkouts por status"""
        checkout_models = CheckoutModel.objects.filter(status=status).order_by('-created_at')
        return [self._model_to_entity(model) for model in checkout_models]
    
    def delete(self, checkout_id: str) -> bool:
        """Remove um checkout"""
        try:
            checkout_model = CheckoutModel.objects.get(id=checkout_id)
            checkout_model.delete()
            return True
        except CheckoutModel.DoesNotExist:
            return False
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Checkout]:
        """Lista todos os checkouts com paginação"""
        checkout_models = CheckoutModel.objects.all()[offset:offset + limit]
        return [self._model_to_entity(model) for model in checkout_models]
    
    def _model_to_entity(self, model: CheckoutModel) -> Checkout:
        """Converte modelo Django para entidade de domínio"""
        # Converte o cliente do modelo para entidade
        client_entity = ClientEntity(
            id=str(model.client.id),
            name=model.client.name,
            cpf=model.client.cpf,
            phone=model.client.phone,
            mobile_phone=model.client.mobile_phone,
            address=None,  # Pode ser implementado se necessário
            user=model.client.user,
            asaas_id=model.client.asaas_id
        )
        
        return Checkout(
            id=str(model.id),
            name=model.name,
            value=model.value,
            client=client_entity,
            installments=model.installments,
            description=model.description,
            status=model.status,
            asaas_id=model.asaas_id,
            checkout_url=model.checkout_url,
            success_url=model.success_url,
            failure_url=model.failure_url,
            expires_url=model.expires_url,
            external_reference=model.external_reference,
            created_at=model.created_at,
            updated_at=model.updated_at,
            expires_at=model.expires_at
        )
