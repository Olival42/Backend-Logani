from modules.cliente.domain.entities.client_entity import Client as ClientEntity
from modules.cliente.domain.entities.address_entity import Address as AddressEntity
from modules.cliente.domain.repositories.client_repository import IClientRepository
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
            province=address_data.get("province")
        )

        client_entity = ClientEntity(
            id=data.get("id"),
            name=data["name"],
            cpf=data["cpf"],
            phone=data.get("phone"),
            mobile_phone=data["mobile_phone"],
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
            "user": user,
            "client": {
                "id": client_obj.id,
                "name": client_obj.name,
                "cpf": client_obj.cpf,
                "phone": client_obj.phone,
                "mobile_phone": client_obj.mobile_phone,
                "registration_date": client_obj.registration_date,
                "active": client_obj.active,
                "asaas_id": client_obj.asaas_id,
                "address": address
            }
        }

    def update_client(self, client_id: str, data: dict) -> ClientEntity:
        existing_client = self.client_repository.get_by_id(client_id)
        if not existing_client:
            raise ValueError("Cliente não encontrado")

        if "address" in data:
            address_data = data["address"]
            updated_address = AddressEntity(
                address=address_data.get("address", existing_client.address.address),
                number=address_data.get("number", existing_client.address.number),
                postal_code=address_data.get("postal_code", existing_client.address.postal_code),
                city=address_data.get("city", existing_client.address.city),
                state=address_data.get("state", existing_client.address.state),
                complement=address_data.get("complement", existing_client.address.complement),
                province=address_data.get("province", existing_client.address.province),
            )
        else:
            updated_address = existing_client.address

        updated_client = ClientEntity(
            id=existing_client.id,
            name=data.get("name", existing_client.name),
            cpf=data.get("cpf", existing_client.cpf),
            phone=data.get("phone", existing_client.phone),
            mobile_phone=data.get("mobile_phone", existing_client.mobile_phone),
            address=updated_address,
            user=existing_client.user,
            asaas_id=data.get("asaas_id", existing_client.asaas_id)
        )

        updated_client = self.client_repository.update(updated_client)
        return updated_client