from abc import ABC, abstractmethod
from modules.cliente.domain.entities.client_entity import Client as ClientEntity

class IClientRepository:
    
    @abstractmethod
    def save(self, client_entity) -> ClientEntity:
        pass

    @abstractmethod
    def get_by_id(self, client_id: str) -> ClientEntity | None:
        pass
    
    @abstractmethod
    def update(self, client_entity) -> ClientEntity:
        pass