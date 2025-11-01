from modules.cliente.domain.entities.client_entity import Client as ClientEntity
from modules.cliente.adapters.persistence.models import Client as ClientModel, Address as AddressModel
from modules.cliente.domain.repositories.client_repository import IClientRepository
from modules.cliente.domain.entities.address_entity import Address as AddressEntity
from uuid import uuid4
from django.db import transaction
from modules.usuario.adapters.persistence.models import User

class ClientRepository(IClientRepository):
    def save(self, client_entity: ClientEntity) -> ClientEntity:
        # Usa transação atômica para garantir que Address e Client sejam salvos juntos
        # Se falhar ao criar Client, o Address também é revertido
        with transaction.atomic():
            address = client_entity.address
            address_model = AddressModel.objects.create(
                address=address.address,
                address_number=address.number,
                postal_code=address.postal_code,
                city=address.city,
                state=address.state,
                complement=address.complement,
                province=address.province
            )

            client_model = ClientModel.objects.create(
                id=client_entity.id or uuid4(),
                name=client_entity.name,
                cpf=client_entity.cpf,
                phone=client_entity.phone,
                mobile_phone=client_entity.mobile_phone,
                address=address_model,
                user=client_entity.user,
                asaas_id=client_entity.asaas_id
            )

            client_entity.id = str(client_model.id)
            return client_entity

    def get_by_id(self, client_id: str) -> ClientEntity | None:
        try:
            client_model = ClientModel.objects.select_related("address", "user").get(id=client_id)
        except ClientModel.DoesNotExist:
            return None

        return self._model_to_entity(client_model)
    
    def get_by_asaas_id(self, asaas_id: str) -> ClientEntity | None:
        try:
            client_model = ClientModel.objects.select_related("address", "user").get(asaas_id=asaas_id)
        except ClientModel.DoesNotExist:
            return None
        
        return self._model_to_entity(client_model)
    
    def get_by_user_id(self, user_id: str) -> ClientEntity | None:
        try:
            client_model = ClientModel.objects.select_related("address", "user").get(user_id=user_id)
        except ClientModel.DoesNotExist:
            return None
        
        return self._model_to_entity(client_model)
    
    def _model_to_entity(self, client_model) -> ClientEntity:
        """
        Converte um modelo Django Client em uma entidade ClientEntity
        """
        address_model = client_model.address
        if address_model:
            address_entity = AddressEntity(
                address=address_model.address,
                number=address_model.address_number,
                postal_code=address_model.postal_code,
                city=address_model.city,
                state=address_model.state,
                complement=address_model.complement,
                province=address_model.province
            )
        else:
            # Cria uma entidade de endereço vazia se não houver endereço
            address_entity = AddressEntity(
                address="",
                number="",
                postal_code="",
                city="",
                state="",
                complement=None,
                province=""
            )

        user_model = client_model.user

        return ClientEntity(
            id=str(client_model.id),
            name=client_model.name,
            cpf=client_model.cpf,
            phone=client_model.phone,
            mobile_phone=client_model.mobile_phone,
            address=address_entity,
            user=user_model,
            asaas_id=client_model.asaas_id
        )

    def update(self, client_entity: ClientEntity) -> ClientEntity:
        try:
            client_model = ClientModel.objects.select_related("address").get(id=client_entity.id)
        except ClientModel.DoesNotExist:
            raise ValueError("Cliente não encontrado para atualização")

        # Usa transação atômica para garantir que Address e Client sejam atualizados juntos
        with transaction.atomic():
            address = client_entity.address
            if client_model.address:
                address_model = client_model.address
                address_model.address = address.address
                address_model.address_number = address.number
                address_model.postal_code = address.postal_code
                address_model.city = address.city
                address_model.state = address.state
                address_model.complement = address.complement
                address_model.province = address.province
                address_model.save()
            else:
                new_address_model = AddressModel.objects.create(
                    address=address.address,
                    address_number=address.number,
                    postal_code=address.postal_code,
                    city=address.city,
                    state=address.state,
                    complement=address.complement,
                    province=address.province
                )
                client_model.address = new_address_model

            client_model.name = client_entity.name
            client_model.cpf = client_entity.cpf
            client_model.phone = client_entity.phone
            client_model.mobile_phone = client_entity.mobile_phone
            client_model.asaas_id = client_entity.asaas_id
            client_model.save()

            return client_entity