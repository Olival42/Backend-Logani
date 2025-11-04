from abc import ABC, abstractmethod
from typing import Optional
from modules.frete.domain.entities.token_entity import Token


class ITokenRepository(ABC):
    """
    Interface para repositório de tokens do Melhor Envio
    """
    
    @abstractmethod
    def save(self, token: Token) -> Token:
        """
        Salva ou atualiza um token
        """
        pass
    
    @abstractmethod
    def get_latest(self) -> Optional[Token]:
        """
        Obtém o token mais recente
        """
        pass
    
    @abstractmethod
    def delete_all(self) -> None:
        """
        Remove todos os tokens (útil para limpar tokens antigos)
        """
        pass

