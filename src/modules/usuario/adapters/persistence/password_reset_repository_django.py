from modules.usuario.adapters.persistence.models import PasswordResetToken, User as UserModel
from modules.usuario.domain.repositories.password_reset_repository import IPasswordResetRepository
from django.utils import timezone
from datetime import timedelta
from typing import Optional

class PasswordResetRepository(IPasswordResetRepository):
    """Implementação Django do repositório de tokens de reset de senha"""
    
    def save_token(self, user_id: int, token_hash: str, expires_at) -> None:
        """Salva um token de reset de senha"""
        user = UserModel.objects.get(id=user_id)
        PasswordResetToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at
        )
    
    def find_by_token_hash(self, token_hash: str) -> Optional[dict]:
        """Busca um token pelo hash"""
        try:
            token = PasswordResetToken.objects.get(token_hash=token_hash)
            return {
                'id': token.id,
                'user_id': token.user.id,
                'token_hash': token.token_hash,
                'created_at': token.created_at,
                'expires_at': token.expires_at,
                'used': token.used,
                'used_at': token.used_at,
                'is_valid': token.is_valid()
            }
        except PasswordResetToken.DoesNotExist:
            return None
    
    def mark_as_used(self, token_hash: str) -> None:
        """Marca um token como usado"""
        try:
            token = PasswordResetToken.objects.get(token_hash=token_hash)
            token.used = True
            token.used_at = timezone.now()
            token.save()
        except PasswordResetToken.DoesNotExist:
            pass
    
    def invalidate_user_tokens(self, user_id: int) -> None:
        """Invalida todos os tokens ativos de um usuário"""
        PasswordResetToken.objects.filter(
            user_id=user_id,
            used=False,
            expires_at__gt=timezone.now()
        ).update(used=True, used_at=timezone.now())
    
    def count_recent_requests(self, user_id: int, minutes: int) -> int:
        """Conta quantas requisições de reset foram feitas recentemente"""
        since = timezone.now() - timedelta(minutes=minutes)
        return PasswordResetToken.objects.filter(
            user_id=user_id,
            created_at__gte=since
        ).count()

