from datetime import datetime, timezone
from modules.cliente.domain.entities.address_entity import Address
from modules.usuario.adapters.persistence.models import User

class Client:
    def __init__(
        self,
        id: str,
        name: str,
        cpf: str,
        phone: str,
        mobile_phone: str,
        address: Address,
        registration_date: datetime = None,
        user: User = None,
        active: bool = True,
        asaas_id: str = None
    ):
        self.id = id
        self.name = name
        self.cpf = cpf
        self.phone = phone
        self.mobile_phone = mobile_phone
        self.address = address
        self.user = user
        self.registration_date = registration_date or datetime.now(timezone.utc)
        self.active = active
        self.asaas_id = asaas_id

    def __repr__(self):
        return f"<Client {self.name} ({self.cpf})>"