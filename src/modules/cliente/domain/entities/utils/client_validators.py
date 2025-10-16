import re
from modules.cliente.domain.entities.utils.cpf_utils import ValidateCpf

class ClientValidators:
    
    def validate_name(name: str):
        if not name or not name.strip():
            raise ValueError("O nome é obrigatório")
        if re.search(r'\d', name):
            raise ValueError("O nome não pode conter números")
        return name

    def validate_cpf(cpf: str):
        cpf = re.sub(r'\D', '', cpf)
        if not cpf or not cpf.strip():
            raise ValueError("CPF é obrigatório")
        ValidateCpf.validate_cpf(cpf)
        return cpf

    def validate_phone(phone: str | None):
        if not phone:
            return None
        digits = re.sub(r'\D', '', phone)
        if len(digits) != 10:
            raise ValueError("Telefone fixo deve ter 10 dígitos (DDD + número)")
        return digits

    def validate_mobile_phone(mobile_phone: str):
        digits = re.sub(r'\D', '', mobile_phone)
        if len(digits) != 11:
            raise ValueError("Celular deve ter 11 dígitos (DDD + número)")
        if digits[2] != "9":
            raise ValueError("Celular inválido, deve começar com 9 após o DDD")
        return digits

    def validate_state_register(type_person: str, state_register: str | None):
        if type_person.upper() == "PJ":
            if not state_register:
                raise ValueError("Inscrição Estadual é obrigatória")
            state_register = state_register.strip().upper()
            if state_register != "ISENTO" and not re.fullmatch(r'\d{8,12}', state_register):
                raise ValueError("Inscrição Estadual inválida, deve conter 8 a 12 dígitos")
            return state_register
        return None
