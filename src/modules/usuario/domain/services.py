from modules.usuario.domain.entities import User
from modules.usuario.domain.repositories.user_repository import IUserRepository
from modules.usuario.domain.utils.jwt_utils import Jwt_Utils

from modules.usuario.domain.repositories.blacklist_repository import IBlacklistRepository
from modules.usuario.domain.repositories.password_reset_repository import IPasswordResetRepository

import os 
import redis 
import logging
import secrets
import hashlib
from dotenv import load_dotenv 
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

load_dotenv() 

REDIS_HOST = os.getenv("REDIS_HOST") 
REDIS_PORT = os.getenv("REDIS_PORT") 
REDIS_DB = os.getenv("REDIS_DB") 

r = redis.Redis(host=str(REDIS_HOST), port=int(REDIS_PORT), db=int(REDIS_DB)) 

MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS")) 
LOCK_TIME_SECONDS = int(os.getenv("LOCK_TIME_SECONDS"))

# Configurações para reset de senha
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "1"))
MAX_PASSWORD_RESET_REQUESTS_PER_HOUR = int(os.getenv("MAX_PASSWORD_RESET_REQUESTS_PER_HOUR", "3"))

class UserService:
    def __init__(self, user_repo: IUserRepository, blacklist_repo: IBlacklistRepository, password_reset_repo: IPasswordResetRepository = None):
        self.user_repo = user_repo
        self.blacklist_repo = blacklist_repo
        self.password_reset_repo = password_reset_repo

    def create_user(self, name: str, email: str, password: str) -> User:
        if self.user_repo.find_by_email(email):
            raise ValueError("Email já cadastrado")
        
        user = User(id=None, name=name, email=email, password=password)
        
        # Usa transação atômica para garantir consistência na criação do usuário
        with transaction.atomic():
            saved_user = self.user_repo.save(user)
        
        access_token = Jwt_Utils.create_access_token(saved_user.id, saved_user.email)
        refresh_token = Jwt_Utils.create_refresh_token(saved_user.id, saved_user.email)
        
        expires_at = Jwt_Utils.decode_token(access_token)["exp"]
        
        return {
            "user": {
                "id": saved_user.id,
                "name": saved_user.name,
                "email": saved_user.email
            },
            "access": access_token,
            "refresh": refresh_token,
            "expires_at": expires_at
        }

    def login_user(self, email: str, password: str) -> dict: 
        user = self.user_repo.find_by_email(email) 
        
        attempts_key = f"login_attempts:{email}" 
        
        attempts = r.get(attempts_key) 
        
        if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS: 
            raise ValueError("Conta temporariamente bloqueada. Tente novamente mais tarde.") 
        
        if not user or not User.verify_password(password, user.password): 
            r.incr(attempts_key) 
            r.expire(attempts_key, LOCK_TIME_SECONDS) 
            raise ValueError("Email ou senha inválidos") 
        
        r.delete(attempts_key) 
        
        access_token = Jwt_Utils.create_access_token(user.id, user.email) 
        refresh_token = Jwt_Utils.create_refresh_token(user.id, user.email) 
        
        payload = Jwt_Utils.decode_token(access_token)
        expires_at = payload["exp"]
        
        return {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            },
            "access": access_token,
            "refresh": refresh_token,
            "expires_at": expires_at
        }
    
    def logout(self, access_token: str, refresh_token: str = None) -> dict:
        try:
            payload = Jwt_Utils.decode_token(access_token)
            
            jti = payload["jti"]
            exp = payload["exp"]
            
            if not self.blacklist_repo.is_blacklisted(jti):
                self.blacklist_repo.add_token(jti, exp)
            
            if refresh_token:
                payload_r = Jwt_Utils.decode_token(refresh_token)
                
                jti_r = payload_r["jti"]
                exp_r = payload_r["exp"]
                
                if not self.blacklist_repo.is_blacklisted(jti_r):
                    self.blacklist_repo.add_token(jti_r, exp_r)
            
            return {"detail": "Logout realizado com sucesso"}
        except ValueError as e:
            return {"detail": str(e)}

        
    def refresh_access_token(self, refresh_token: str) -> dict: 
        try: 
            payload = Jwt_Utils.decode_token(refresh_token)
            
            jti = payload["jti"] 
            exp = payload["exp"]
            
            if self.blacklist_repo.is_blacklisted(jti): 
                raise ValueError("Refresh token revogado") 
            
            # Revoga o refresh token antigo
            self.blacklist_repo.add_token(jti, exp)
            
            # Gera novos tokens
            new_access_token = Jwt_Utils.create_access_token(payload["user_id"], payload["email"]) 
            new_refresh_token = Jwt_Utils.create_refresh_token(payload["user_id"], payload["email"])
            
            # Obtém o expires_at do novo access token
            new_payload = Jwt_Utils.decode_token(new_access_token)
            expires_at = new_payload["exp"]
            
            return {
                "access": new_access_token,
                "refresh": new_refresh_token,
                "expires_at": expires_at
            } 
        except ValueError as e: 
            raise ValueError(str(e))
        
    def authenticate(self, token: str) -> dict:
        payload = Jwt_Utils.decode_token(token)
        
        if self.blacklist_repo.is_blacklisted(payload["jti"]):
            raise ValueError("Token revogado")
        
        return payload
    
    def update_user(self, user_id: int, name: str = None, password: str = None) -> dict:
        """
        Atualiza informações do usuário
        Apenas os campos name e password podem ser atualizados
        """
        # Busca o usuário
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado")
        
        # Atualiza apenas os campos fornecidos
        updated_name = name if name is not None else user.name
        updated_password = user.password  # Mantém a senha atual por padrão
        
        # Se senha foi fornecida, atualiza
        if password:
            # Valida a nova senha
            User.validate_password(password)
            # Cria nova instância com a nova senha para gerar o hash
            temp_user = User(id=user.id, name=user.name, email=user.email, password=password)
            updated_password = temp_user.password
        
        # Cria instância atualizada do usuário
        # Mantém email e active originais (não podem ser alterados)
        updated_user = User(
            id=user.id,
            name=updated_name,
            email=user.email,  # Mantém o email original
            password=updated_password,
            registration_date=user.registration_date,
            active=user.active,  # Mantém o status active original
            _is_hashed=True
        )
        
        # Salva com transação atômica
        with transaction.atomic():
            saved_user = self.user_repo.save(updated_user)
        
        # Se o nome foi alterado, atualiza também o cliente associado
        if name is not None and name != user.name:
            try:
                # Importa repositórios e serviços de cliente
                from modules.cliente.adapters.persistence.client_repository_django import ClientRepository
                from modules.cliente.adapters.external.asaas_client import AsaasClient
                
                client_repository = ClientRepository()
                client = client_repository.get_by_user_id(str(user_id))
                
                if client:
                    logger = logging.getLogger(__name__)
                    logger.info(f"Atualizando cliente {client.id} - nome antigo: '{client.name}' -> novo: '{saved_user.name}'")
                    
                    # Atualiza o nome do cliente com o novo nome do usuário
                    # Cria uma nova entidade com o nome atualizado, mantendo todos os outros campos
                    from modules.cliente.domain.entities.client_entity import Client as ClientEntity
                    from modules.usuario.adapters.persistence.models import User as UserModel
                    
                    # Busca o modelo Django User atualizado
                    user_model = UserModel.objects.get(id=user_id)
                    
                    updated_client_entity = ClientEntity(
                        id=client.id,
                        name=saved_user.name,  # Novo nome do usuário
                        cpf=client.cpf,
                        phone=client.phone,
                        mobile_phone=client.mobile_phone,
                        address=client.address,
                        user=user_model,  # Usa o modelo Django User atualizado
                        registration_date=client.registration_date,
                        active=client.active,
                        asaas_id=client.asaas_id
                    )
                    
                    # Atualiza no banco local
                    client_repository.update(updated_client_entity)
                    logger.info(f"Cliente atualizado no banco local: {updated_client_entity.name}")
                    
                    # Se o cliente tem ID no Asaas, atualiza também lá
                    if updated_client_entity.asaas_id:
                        try:
                            asaas_client = AsaasClient()
                            asaas_response = asaas_client.update_customer(updated_client_entity.asaas_id, updated_client_entity)
                            logger.info(f"Cliente atualizado no Asaas (ID: {updated_client_entity.asaas_id}): {asaas_response}")
                        except Exception as e:
                            # Log do erro mas não interrompe a atualização do usuário
                            # O nome já foi atualizado no banco local
                            logger.error(f"Erro ao atualizar cliente no Asaas: {str(e)}", exc_info=True)
                else:
                    logger.warning(f"Cliente não encontrado para o usuário {user_id}")
            except Exception as e:
                # Log do erro mas não interrompe a atualização do usuário
                # O nome já foi atualizado no banco local
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao atualizar cliente associado: {str(e)}", exc_info=True)
        
        return {
            "user": {
                "id": saved_user.id,
                "name": saved_user.name,
                "email": saved_user.email,
                "active": saved_user.active
            }
        }
    
    def request_password_reset(self, email: str) -> dict:
        """
        Solicita reset de senha para um email
        Implementa rate limiting e não revela se o email existe
        """
        if not self.password_reset_repo:
            raise ValueError("Password reset repository não configurado")
        
        # Busca o usuário (sem revelar se existe ou não)
        user = self.user_repo.find_by_email(email)
        
        # Se o usuário não existe, retorna sucesso mesmo assim (para não revelar emails)
        if not user:
            # Retorna sucesso mas não envia email
            return {
                "message": "Se o email estiver cadastrado, você receberá um link para resetar sua senha"
            }
        
        # Verifica se o usuário está ativo
        if not user.active:
            # Retorna sucesso mesmo assim para não revelar que a conta está inativa
            return {
                "message": "Se o email estiver cadastrado, você receberá um link para resetar sua senha"
            }
        
        # Rate limiting: verifica quantas requisições foram feitas na última hora
        recent_requests = self.password_reset_repo.count_recent_requests(
            user.id, 
            minutes=60
        )
        
        if recent_requests >= MAX_PASSWORD_RESET_REQUESTS_PER_HOUR:
            # Retorna sucesso mesmo assim para não revelar o rate limit
            return {
                "message": "Se o email estiver cadastrado, você receberá um link para resetar sua senha"
            }
        
        # Invalida tokens anteriores do usuário
        self.password_reset_repo.invalidate_user_tokens(user.id)
        
        # Gera token seguro
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Define expiração
        expires_at = timezone.now() + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        
        # Salva o token
        with transaction.atomic():
            self.password_reset_repo.save_token(user.id, token_hash, expires_at)
        
        # Retorna o token (será usado para enviar o email)
        return {
            "message": "Se o email estiver cadastrado, você receberá um link para resetar sua senha",
            "token": token,  # Token será usado apenas para enviar o email
            "user_email": user.email,
            "user_name": user.name
        }
    
    def reset_password(self, token: str, new_password: str) -> dict:
        """
        Reseta a senha usando um token válido
        """
        if not self.password_reset_repo:
            raise ValueError("Password reset repository não configurado")
        
        # Valida a nova senha
        User.validate_password(new_password)
        
        # Hash do token para buscar no banco
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Busca o token
        token_data = self.password_reset_repo.find_by_token_hash(token_hash)
        
        if not token_data:
            raise ValueError("Token inválido ou expirado")
        
        # Verifica se o token é válido
        if not token_data['is_valid']:
            raise ValueError("Token inválido ou expirado")
        
        # Busca o usuário
        user = self.user_repo.find_by_id(token_data['user_id'])
        if not user:
            raise ValueError("Usuário não encontrado")
        
        # Atualiza a senha
        with transaction.atomic():
            # Marca o token como usado
            self.password_reset_repo.mark_as_used(token_hash)
            
            # Atualiza a senha do usuário
            temp_user = User(
                id=user.id,
                name=user.name,
                email=user.email,
                password=new_password
            )
            updated_user = User(
                id=user.id,
                name=user.name,
                email=user.email,
                password=temp_user.password,
                registration_date=user.registration_date,
                active=user.active,
                _is_hashed=True
            )
            self.user_repo.save(updated_user)
        
        return {
            "message": "Senha alterada com sucesso"
        }