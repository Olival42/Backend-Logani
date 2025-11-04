from typing import Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from modules.frete.domain.entities.token_entity import Token
from modules.frete.domain.repositories.token_repository import ITokenRepository
from modules.frete.adapters.persistence.models import MelhorEnvioToken as MelhorEnvioTokenModel


class TokenRepositoryDjango(ITokenRepository):
    """
    Implementação Django do repositório de tokens
    Prioriza token da variável de ambiente se disponível
    """
    
    def save(self, token: Token) -> Token:
        """
        Salva ou atualiza um token
        Por padrão, mantém apenas um token ativo
        """
        # Remove tokens antigos
        MelhorEnvioTokenModel.objects.all().delete()
        
        try:
            # Cria novo token
            # Usa None se refresh_token estiver vazio (para evitar problemas com unique constraint)
            refresh_token_value = token.refresh_token if (token.refresh_token and len(token.refresh_token.strip()) > 0) else None
            
            model = MelhorEnvioTokenModel.objects.create(
                access_token=token.access_token,
                refresh_token=refresh_token_value,
                expires_in=token.expires_in,
                token_type=token.token_type,
                created_at=token.created_at or timezone.now()
            )
        except Exception as e:
            # Se houver erro de unicidade, tenta novamente após limpar
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                MelhorEnvioTokenModel.objects.all().delete()
                refresh_token_value = token.refresh_token if (token.refresh_token and len(token.refresh_token.strip()) > 0) else None
                model = MelhorEnvioTokenModel.objects.create(
                    access_token=token.access_token,
                    refresh_token=refresh_token_value,
                    expires_in=token.expires_in,
                    token_type=token.token_type,
                    created_at=token.created_at or timezone.now()
                )
            else:
                raise ValueError(f"Erro ao salvar token no banco de dados: {str(e)}")
        
        return Token(
            access_token=model.access_token,
            refresh_token=model.refresh_token,
            expires_in=model.expires_in,
            token_type=model.token_type,
            created_at=model.created_at
        )
    
    def get_latest(self) -> Optional[Token]:
        """
        Obtém o token mais recente
        Prioriza token da variável de ambiente se disponível
        """
        # Verifica se há token na variável de ambiente (prioridade)
        access_token_env = getattr(settings, 'MELHOR_ENVIO_ACCESS_TOKEN', None)
        
        if access_token_env:
            # Limpa o token (remove espaços e "Bearer" se presente)
            token_value = access_token_env.strip()
            if token_value.startswith('Bearer '):
                token_value = token_value[7:].strip()
            
            # Retorna token da variável de ambiente
            # Assume que não expira (ou expira em 30 dias)
            return Token(
                access_token=token_value,
                refresh_token='',  # Não há refresh token quando vem do .env
                expires_in=2592000,  # 30 dias em segundos
                token_type='Bearer',
                created_at=timezone.now() - timedelta(days=1)  # Assume que foi criado há 1 dia
            )
        
        # Se não há token no .env, busca no banco
        try:
            model = MelhorEnvioTokenModel.objects.latest('created_at')
            return Token(
                access_token=model.access_token,
                refresh_token=model.refresh_token,
                expires_in=model.expires_in,
                token_type=model.token_type,
                created_at=model.created_at
            )
        except MelhorEnvioTokenModel.DoesNotExist:
            return None
    
    def delete_all(self) -> None:
        """
        Remove todos os tokens
        """
        MelhorEnvioTokenModel.objects.all().delete()

