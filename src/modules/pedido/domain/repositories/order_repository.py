from abc import ABC, abstractmethod
from modules.pedido.domain.entities.order_entity import Order
from typing import List, Optional


class IOrderRepository(ABC):
    """Interface para repositório de pedidos"""
    
    @abstractmethod
    def save(self, order: Order) -> Order:
        pass
    
    @abstractmethod
    def get_by_id(self, order_id: str) -> Optional[Order]:
        pass
    
    @abstractmethod
    def get_by_client(self, client_id: str) -> List[Order]:
        pass
    
    @abstractmethod
    def get_by_external_reference(self, external_reference: str) -> Optional[Order]:
        pass
    
    @abstractmethod
    def get_by_status(self, status: str) -> List[Order]:
        pass
    
    @abstractmethod
    def update(self, order: Order) -> Order:
        pass
    
    @abstractmethod
    def list_all(self) -> List[Order]:
        pass

