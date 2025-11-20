from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from django.utils import timezone


@dataclass
class Token:
    """
    Entidade que representa um token de autenticação do Melhor Envio
    """
    access_token: str
    refresh_token: str
    expires_in: int  # em segundos
    token_type: str = "Bearer"
    created_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """
        Verifica se o token está expirado
        """
        if not self.created_at:
            return True
        
        # Garante que ambos os datetimes sejam timezone-aware
        if self.created_at.tzinfo is None:
            # Se created_at é naive, torna-o aware usando timezone.now() como referência
            created_at_aware = timezone.make_aware(self.created_at)
        else:
            created_at_aware = self.created_at
        
        expires_at = created_at_aware + timedelta(seconds=self.expires_in)
        return timezone.now() >= expires_at

