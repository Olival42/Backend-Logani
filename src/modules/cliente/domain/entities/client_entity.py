from datetime import datetime, timezone
from modules.cliente.domain.entities.address_entity import Address
from modules.cliente.domain.entities.utils.cpf_cnpj_utils import ValidateCpfCnpj
import re

class Client:
    def __init__(
        self,
        id: str,
        name: str,
        type_person: str,
        cpf_cnpj: str,
        phone: str | None = None,
        mobile_phone: str | None = None,
        state_register: str | None = None,
        address: Address | None = None,
        user=None,
        registration_date: datetime | None = None,
        active: bool = True,
        asaas_id: str | None = None
    ):
        if not name or not cpf_cnpj or not mobile_phone or not address:
            raise ValueError("Preencha todos os campos obrigatórios.")
        if not user:
            raise ValueError("User é obrigatório")
        
        self.id = id
        self.name = self.validate_name(name)
        self.type_person = type_person.upper()
        if self.type_person not in ("PF", "PJ"):
            raise ValueError("type_person deve ser 'PF' ou 'PJ'")
        self.cpf_cnpj = self.validate_cpf_cnpj(cpf_cnpj)
        self.phone = self.validate_phone(phone)
        self.mobile_phone = self.validate_mobile_phone(mobile_phone)
        self.state_register = self.validate_sr(state_register)
        self.address = address
        self.user = user
        self.registration_date = registration_date or datetime.now(timezone.utc)
        self.active = active
        self.asaas_id = asaas_id

    def __repr__(self):
        return f"<Client {self.name} ({self.cpf_cnpj})>"

    def validate_name(self, name: str):
        if re.search(r'\d', name):
            raise ValueError("O nome não pode conter números")
        return name

    def validate_cpf_cnpj(self, cpf_cnpj: str):
        cpf_cnpj = re.sub(r'\D', '', cpf_cnpj)
        if self.type_person == "PF":
            ValidateCpfCnpj.validate_cpf(cpf_cnpj)
        else:
            ValidateCpfCnpj.validate_cnpj(cpf_cnpj)
        return cpf_cnpj

    def validate_phone(self, phone: str | None):
        if not phone:
            return None

        phone_digits = re.sub(r'\D', '', phone)
        if len(phone_digits) != 10:
            raise ValueError("Telefone fixo deve ter 10 dígitos (DDD + número)")
        return phone_digits

    def validate_mobile_phone(self, mobile_phone: str):
        if not mobile_phone:
            raise ValueError("Celular é obrigatório")

        phone_digits = re.sub(r'\D', '', mobile_phone)
        if len(phone_digits) != 11:
            raise ValueError("Celular deve ter 11 dígitos (DDD + número)")

        if phone_digits[2] != "9":
            raise ValueError("Celular inválido, deve começar com 9 após o DDD")

        return phone_digits
    
    def validate_sr(self, ie: str | None) -> str | None:
        if self.type_person == "PJ":
            if not ie:
                raise ValueError("Inscrição Estadual é obrigatória")
            ie = ie.strip().upper()
            if ie == "ISENTO":
                return ie
            if not re.fullmatch(r'\d{8,12}', ie):
                raise ValueError("Inscrição Estadual inválida, deve conter 8 a 12 dígitos")
            return ie
        return None
