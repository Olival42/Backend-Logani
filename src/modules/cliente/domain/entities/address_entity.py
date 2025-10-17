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
        
        self.address = address
        self.number = number
        self.postal_code = postal_code
        self.city = city
        self.state = state.upper()
        self.complement = complement
        self.province = province

    def __repr__(self):
        return f"<Address {self.address}, {self.number}, {self.postal_code}>"
