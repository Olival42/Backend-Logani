from abc import ABC, abstractmethod
from modules.usuario.domain.entities import User

class IUserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> User:
        pass
    
    @abstractmethod
    def find_by_email(self, email:str) -> User:
        pass