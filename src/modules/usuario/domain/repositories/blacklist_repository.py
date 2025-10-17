from abc import ABC, abstractmethod

class IBlacklistRepository(ABC):
    @abstractmethod
    def add_token(self, jti: str, exp: int):
        pass

    @abstractmethod
    def is_blacklisted(self, jti: str) -> bool:
        pass