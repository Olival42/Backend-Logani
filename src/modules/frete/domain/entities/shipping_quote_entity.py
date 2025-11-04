from dataclasses import dataclass
from typing import Optional
from decimal import Decimal


@dataclass
class ShippingQuote:
    """
    Entidade que representa uma cotação de frete do Melhor Envio
    """
    id: int
    name: str
    price: Decimal
    delivery_time: int  # dias - campos sem default devem vir primeiro
    custom_price: Optional[Decimal] = None
    currency: str = "BRL"
    custom_delivery_time: Optional[int] = None
    company: dict = None  # informações da transportadora
    
    def get_final_price(self) -> Decimal:
        """
        Retorna o preço final considerando custom_price se disponível
        """
        return self.custom_price if self.custom_price is not None else self.price
    
    def get_final_delivery_time(self) -> int:
        """
        Retorna o prazo final considerando custom_delivery_time se disponível
        """
        return self.custom_delivery_time if self.custom_delivery_time is not None else self.delivery_time

