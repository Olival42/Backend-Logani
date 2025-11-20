from abc import ABC, abstractmethod
from typing import Optional

class IPasswordResetRepository(ABC):
    """Interface para repositório de tokens de reset de senha"""
    
    @abstractmethod
    def save_token(self, user_id: int, token_hash: str, expires_at) -> None:
        """Salva um token de reset de senha"""
        pass
    
    @abstractmethod
    def find_by_token_hash(self, token_hash: str) -> Optional[dict]:
        """Busca um token pelo hash"""
        pass
    
    @abstractmethod
    def mark_as_used(self, token_hash: str) -> None:
        """Marca um token como usado"""
        pass
    
    @abstractmethod
    def invalidate_user_tokens(self, user_id: int) -> None:
        """Invalida todos os tokens ativos de um usuário"""
        pass
    
    @abstractmethod
    def count_recent_requests(self, user_id: int, minutes: int) -> int:
        """Conta quantas requisições de reset foram feitas recentemente"""
        pass

