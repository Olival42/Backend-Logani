import re

class Address:
    def __init__(
        self,
        address: str,
        number: str,
        postal_code: str,
        city: str,
        state: str,
        complement: str,
        province: str
    ):
        if not address or not number or not postal_code or not city or not state or not province:
            raise ValueError("Preencha todos os campos obrigatórios.")
        
        self.address = address
        self.number = number
        self.postal_code = self.validate_postal_code(postal_code)
        self.city = city
        self.state = self.validate_state(state)
        self.complement = complement
        self.province = province

    def validate_postal_code(self, postal_code: str) -> str:
        digits = re.sub(r'\D', '', postal_code)
        if len(digits) != 8:
            raise ValueError("CEP inválido, deve conter 8 dígitos")
        return digits
    
    def validate_state(self, state: str) -> str:
        if len(state) != 2:
            raise ValueError("Estado inválido, deve conter 2 caracteres")
        return state

    def __repr__(self):
        return f"<Address {self.address}, {self.number}, {self.postal_code}>"
