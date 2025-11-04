from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Product:
    """
    Entidade que representa um produto para cálculo de frete
    """
    id: str
    width: Decimal  # largura em cm
    height: Decimal  # altura em cm
    length: Decimal  # comprimento em cm
    weight: Decimal  # peso em kg
    insurance_value: Decimal  # valor para seguro
    quantity: int = 1
    
    def to_melhor_envio_format(self) -> dict:
        """
        Converte o produto para o formato esperado pela API do Melhor Envio
        """
        return {
            "id": self.id,
            "width": float(self.width),
            "height": float(self.height),
            "length": float(self.length),
            "weight": float(self.weight),
            "insurance_value": float(self.insurance_value),
            "quantity": self.quantity
        }

