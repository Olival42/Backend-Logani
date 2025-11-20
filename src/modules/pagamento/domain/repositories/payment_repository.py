from abc import ABC, abstractmethod
from modules.pagamento.domain.entities.payment_entity import Payment
from typing import List, Optional


class IPaymentRepository(ABC):
    """Interface para repositório de pagamentos"""
    
    @abstractmethod
    def save(self, payment: Payment) -> Payment:
        pass
    
    @abstractmethod
    def get_by_id(self, payment_id: str) -> Optional[Payment]:
        pass
    
    @abstractmethod
    def get_by_client(self, client_id: str) -> List[Payment]:
        pass
    
    @abstractmethod
    def get_by_asaas_id(self, asaas_id: str) -> Optional[Payment]:
        pass
    
    @abstractmethod
    def get_by_asaas_checkout_id(self, asaas_checkout_id: str) -> Optional[Payment]:
        pass
    
    @abstractmethod
    def get_by_external_reference(self, external_reference: str) -> Optional[Payment]:
        pass
    
    @abstractmethod
    def get_by_status(self, status: str) -> List[Payment]:
        pass
    
    @abstractmethod
    def get_by_order(self, order_id: str) -> List[Payment]:
        pass
    
    @abstractmethod
    def get_by_installment_id(self, installment_id: str) -> List[Payment]:
        pass
    
    @abstractmethod
    def update(self, payment: Payment) -> Payment:
        pass
    
    @abstractmethod
    def list_all(self) -> List[Payment]:
        pass

