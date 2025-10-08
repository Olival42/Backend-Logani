from modules.cliente.domain.entities.client_entity import Client as ClientEntity
from modules.cliente.domain.repositories.client_repository import IClientRepository
from modules.cliente.domain.entities.address_entity import Address as AddressEntity

from modules.usuario.adapters.persistence.models import User

class ClientService:
    
    def __init__(self, client_repository: IClientRepository):
        self.client_repository = client_repository
    
    def create_client(self, data: dict, user_id: int) -> ClientEntity:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User não encontrado")

        address_data = data.pop("address")
        address_entity = AddressEntity(
            address=address_data.get("address"),
            number=address_data.get("number"),
            postal_code=address_data.get("postal_code"),
            city=address_data.get("city"),
            state=address_data.get("state"),
            complement=address_data.get("complement", ""),
            province=address_data.get("province", "")
        )

        client_entity = ClientEntity(
            id=data.get("id"),
            name=data["name"],
            cpf_cnpj=data["cpf_cnpj"],
            type_person=data["type_person"],
            phone=data.get("phone"),
            mobile_phone=data["mobile_phone"],
            state_register=data.get("state_register"),
            address=address_entity,
            user=user,
            asaas_id=data.get("asaas_id")
        )


        self.client_repository.save(client_entity)

        return client_entity
    
    def get_client_by_id(self, client_id: str) -> dict:
        client_obj = self.client_repository.get_by_id(client_id)
        if not client_obj:
            raise ValueError("Cliente não encontrado")

        address = None
        if client_obj.address:
            address = {
                "address": client_obj.address.address,
                "number": client_obj.address.number,
                "postal_code": client_obj.address.postal_code,
                "city": client_obj.address.city,
                "state": client_obj.address.state,
                "complement": client_obj.address.complement,
                "province": client_obj.address.province,
            }

        user = {
            "id": client_obj.user.id,
            "name": client_obj.user.name,
            "email": client_obj.user.email,
        }

        return {
            "id": client_obj.id,
            "name": client_obj.name,
            "type_person": client_obj.type_person,
            "cpf_cnpj": client_obj.cpf_cnpj,
            "state_register": client_obj.state_register,
            "phone": client_obj.phone,
            "mobile_phone": client_obj.mobile_phone,
            "registration_date": client_obj.registration_date,
            "active": client_obj.active,
            "asaas_id": client_obj.asaas_id,
            "user": user,
            "address": address,
        }