from modules.cliente.domain.entities.client_entity import Client as ClientEntity
from modules.cliente.adapters.persistence.models import Client as ClientModel, Address as AddressModel
from modules.cliente.domain.repositories.client_repository import IClientRepository
from uuid import uuid4
from modules.usuario.adapters.persistence.models import User as User
from modules.cliente.domain.entities.address_entity import Address as AddressEntity

class ClientRepository(IClientRepository):
    def save(self, client_entity: ClientEntity) -> ClientEntity:
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
            cpf_cnpj=client_entity.cpf_cnpj,
            type_person=client_entity.type_person,
            state_register=getattr(client_entity, "state_register", None),
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

        address_model = client_model.address
        address_entity = None
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

        user_model = client_model.user

        return ClientEntity(
            id=str(client_model.id),
            name=client_model.name,
            cpf_cnpj=client_model.cpf_cnpj,
            type_person=client_model.type_person,
            phone=client_model.phone,
            mobile_phone=client_model.mobile_phone,
            state_register=client_model.state_register,
            address=address_entity,
            user=user_model,
            asaas_id=client_model.asaas_id
        )
