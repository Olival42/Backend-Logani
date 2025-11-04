from typing import Optional
from modules.frete.domain.entities.token_entity import Token
from modules.frete.domain.repositories.token_repository import ITokenRepository
from modules.frete.adapters.external.melhor_envio_client import MelhorEnvioClient


class MelhorEnvioAuthService:
    """
    Serviço para gerenciar autenticação com o Melhor Envio
    """
    
    def __init__(self, token_repository: ITokenRepository, client: MelhorEnvioClient):
        self.token_repository = token_repository
        self.client = client
    
    def authenticate_with_code(self, authorization_code: str, redirect_uri: Optional[str] = None) -> Token:
        """
        Autentica usando código de autorização (primeiro acesso)
        
        Args:
            authorization_code: Código de autorização obtido após redirecionamento
            redirect_uri: URI de redirecionamento (opcional)
            
        Returns:
            Token salvo
        """
        token = self.client.request_token(authorization_code, redirect_uri)
        return self.token_repository.save(token)
    
    def refresh_access_token(self) -> Token:
        """
        Renova o token de acesso usando o refresh_token salvo
        
        Returns:
            Token atualizado
            
        Raises:
            ValueError: Se não houver refresh_token salvo
        """
        current_token = self.token_repository.get_latest()
        
        if not current_token:
            raise ValueError("Nenhum token encontrado. É necessário autenticar primeiro.")
        
        if not current_token.refresh_token:
            raise ValueError("Refresh token não encontrado. É necessário autenticar novamente.")
        
        new_token = self.client.refresh_token(current_token.refresh_token)
        return self.token_repository.save(new_token)
    
    def get_valid_token(self) -> Optional[Token]:
        """
        Obtém um token válido (renova se necessário)
        
        Returns:
            Token válido ou None se não houver token salvo
        """
        token = self.token_repository.get_latest()
        
        if not token:
            return None
        
        # Se o token vem do .env (sem refresh_token), sempre considera válido
        if not token.refresh_token:
            return token
        
        # Se o token está expirado, tenta renovar
        if token.is_expired():
            try:
                token = self.refresh_access_token()
            except Exception:
                # Se falhar ao renovar, retorna None
                return None
        
        return token
    
    def ensure_valid_token(self) -> Token:
        """
        Garante que temos um token válido (renova se necessário ou lança exceção)
        
        Returns:
            Token válido
            
        Raises:
            ValueError: Se não for possível obter um token válido
        """
        token = self.get_valid_token()
        
        if not token:
            raise ValueError(
                "Token não disponível. É necessário autenticar primeiro usando o endpoint de autenticação."
            )
        
        return token

