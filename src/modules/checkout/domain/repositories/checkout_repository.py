from abc import ABC, abstractmethod
from typing import List, Optional
from modules.checkout.domain.entities.checkout_entity import Checkout


class ICheckoutRepository(ABC):
    """
    Interface para repositório de checkout
    """
    
    @abstractmethod
    def save(self, checkout: Checkout) -> Checkout:
        """Salva um checkout"""
        pass
    
    @abstractmethod
    def get_by_id(self, checkout_id: str) -> Optional[Checkout]:
        """Busca um checkout por ID"""
        pass
    
    @abstractmethod
    def get_by_asaas_id(self, asaas_id: str) -> Optional[Checkout]:
        """Busca um checkout por ID do ASAAS"""
        pass
    
    @abstractmethod
    def get_by_client(self, client_id: str) -> List[Checkout]:
        """Busca checkouts por cliente"""
        pass
    
    @abstractmethod
    def get_by_status(self, status: str) -> List[Checkout]:
        """Busca checkouts por status"""
        pass
    
    @abstractmethod
    def delete(self, checkout_id: str) -> bool:
        """Remove um checkout"""
        pass
    
    @abstractmethod
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Checkout]:
        """Lista todos os checkouts com paginação"""
        pass