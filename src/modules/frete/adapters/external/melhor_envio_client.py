import requests
from typing import Dict, Optional, Any, List
from django.conf import settings
from django.utils import timezone
from modules.frete.domain.entities.token_entity import Token
from modules.frete.domain.entities.shipping_quote_entity import ShippingQuote
from decimal import Decimal


class MelhorEnvioClient:
    """
    Cliente para integração com a API do Melhor Envio
    """
    
    def __init__(self):
        # Determina se está em ambiente sandbox ou produção
        env = getattr(settings, 'MELHOR_ENVIO_ENVIRONMENT', 'sandbox')
        if env == 'sandbox':
            self.base_url = 'https://sandbox.melhorenvio.com.br'
        else:
            self.base_url = 'https://melhorenvio.com.br'
        
        self.client_id = getattr(settings, 'MELHOR_ENVIO_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'MELHOR_ENVIO_CLIENT_SECRET', None)
        self.redirect_uri = getattr(settings, 'MELHOR_ENVIO_REDIRECT_URI', None)
        
        # Validação mais específica
        if not self.client_id:
            raise ValueError("MELHOR_ENVIO_CLIENT_ID não configurado no .env")
        if not self.client_secret:
            raise ValueError("MELHOR_ENVIO_CLIENT_SECRET não configurado no .env")
    
    def _get_headers(self, access_token: Optional[str] = None) -> Dict[str, str]:
        """
        Retorna os headers padrão para requisições à API do Melhor Envio
        """
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'API Pagamento Frete (integracao@api-pagamento-frete.com)'  # Obrigatório pela API
        }
        
        if access_token:
            # Remove "Bearer " se já estiver presente no token
            token = access_token.strip()
            if token.startswith('Bearer '):
                token = token[7:].strip()
            headers['Authorization'] = f'Bearer {token}'
        
        return headers
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Realiza uma requisição HTTP para a API do Melhor Envio
        
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint da API (sem a URL base)
            data: Dados para enviar no corpo da requisição
            access_token: Token de acesso para autenticação
            
        Returns:
            Dict com a resposta da API
            
        Raises:
            requests.RequestException: Em caso de erro na requisição
            ValueError: Em caso de erro na resposta da API
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers(access_token)
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
            
            response.raise_for_status()
            
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                return {'success': True, 'data': response.text}
                
        except requests.exceptions.HTTPError as e:
            error_detail = "Erro na API do Melhor Envio"
            status_code = e.response.status_code
            
            try:
                error_response = e.response.json()
                if isinstance(error_response, dict):
                    error_detail = error_response.get('message', error_detail)
                    if 'errors' in error_response:
                        errors = error_response['errors']
                        if isinstance(errors, list) and len(errors) > 0:
                            error_detail = errors[0].get('message', error_detail)
                    # Captura mensagem de erro direta
                    if 'error' in error_response:
                        error_detail = error_response.get('error', error_detail)
            except (ValueError, KeyError, IndexError):
                # Se não conseguir parsear JSON, tenta pegar o texto
                try:
                    error_detail = e.response.text[:200]  # Primeiros 200 caracteres
                except:
                    pass
            
            # Mensagem mais específica para 401
            if status_code == 401:
                error_detail = f"Token inválido ou expirado. Verifique se o token está correto no .env (ACESS_TOKEN_MELHOR_ENVIO). Erro original: {error_detail}"
            
            raise ValueError(f"{error_detail} (Status: {status_code})")
        
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Erro de conexão com a API do Melhor Envio: {str(e)}")
    
    def _make_oauth_request(self, method: str, endpoint: str, data: Dict) -> Dict[str, Any]:
        """
        Realiza uma requisição OAuth usando form-urlencoded (não JSON)
        OAuth usa uma URL diferente (auth.melhorenvio.com.br)
        """
        # OAuth usa auth.melhorenvio.com.br, não a URL base da API
        env = getattr(settings, 'MELHOR_ENVIO_ENVIRONMENT', 'sandbox')
        if env == 'sandbox':
            oauth_base_url = 'https://sandbox.melhorenvio.com.br'
        else:
            oauth_base_url = 'https://auth.melhorenvio.com.br'
        
        url = f"{oauth_base_url}/{endpoint.lstrip('/')}"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        # Valida se os dados necessários estão presentes
        if 'client_id' in data and not data['client_id']:
            raise ValueError("client_id não pode estar vazio")
        if 'client_secret' in data and not data['client_secret']:
            raise ValueError("client_secret não pode estar vazio")
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                return {'success': True, 'data': response.text}
                
        except requests.exceptions.HTTPError as e:
            error_detail = "Erro na API do Melhor Envio"
            status_code = e.response.status_code
            
            try:
                error_response = e.response.json()
                if isinstance(error_response, dict):
                    error_detail = error_response.get('message', error_detail)
                    if 'errors' in error_response:
                        errors = error_response['errors']
                        if isinstance(errors, list) and len(errors) > 0:
                            error_detail = errors[0].get('message', error_detail)
                    if 'error' in error_response:
                        error_detail = error_response.get('error', error_detail)
                    if 'error_description' in error_response:
                        error_detail = f"{error_detail}: {error_response.get('error_description', '')}"
            except (ValueError, KeyError, IndexError):
                try:
                    error_detail = e.response.text[:200]
                except:
                    pass
            
            # Mensagens mais específicas para erros comuns
            if status_code == 401:
                if 'invalid_client' in error_detail.lower():
                    error_detail = f"Credenciais inválidas (client_id ou client_secret incorretos). Verifique MELHOR_ENVIO_CLIENT_ID e MELHOR_ENVIO_CLIENT_SECRET no .env. Erro: {error_detail}"
                elif 'invalid_grant' in error_detail.lower() or 'invalid_code' in error_detail.lower():
                    error_detail = f"Código de autorização inválido ou expirado. Códigos só podem ser usados uma vez e expiram rapidamente. Gere um novo código. Erro: {error_detail}"
            
            raise ValueError(f"{error_detail} (Status: {status_code})")
        
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Erro de conexão com a API do Melhor Envio: {str(e)}")
    
    def request_token(self, authorization_code: str, redirect_uri: Optional[str] = None) -> Token:
        """
        Solicita um token de acesso usando o código de autorização (primeiro acesso)
        
        Args:
            authorization_code: Código de autorização obtido após redirecionamento
            redirect_uri: URI de redirecionamento (opcional, usa o padrão se não informado)
            
        Returns:
            Token com access_token e refresh_token
        """
        endpoint = '/oauth/token'
        
        redirect_uri_final = redirect_uri or self.redirect_uri
        if not redirect_uri_final:
            raise ValueError("redirect_uri deve ser informado ou configurado em MELHOR_ENVIO_REDIRECT_URI")
        
        # Valida se client_id e client_secret estão configurados
        if not self.client_id:
            raise ValueError("MELHOR_ENVIO_CLIENT_ID não configurado. Verifique o .env")
        if not self.client_secret:
            raise ValueError("MELHOR_ENVIO_CLIENT_SECRET não configurado. Verifique o .env")
        
        # OAuth usa form-urlencoded, não JSON
        # Remove espaços, quebras de linha e caracteres especiais
        client_id_clean = str(self.client_id).strip().replace('\n', '').replace('\r', '')
        client_secret_clean = str(self.client_secret).strip().replace('\n', '').replace('\r', '')
        redirect_uri_clean = redirect_uri_final.strip().replace('\n', '').replace('\r', '')
        code_clean = authorization_code.strip().replace('\n', '').replace('\r', '')
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': client_id_clean,
            'client_secret': client_secret_clean,
            'redirect_uri': redirect_uri_clean,
            'code': code_clean
        }
        
        # Validação adicional antes de enviar
        if not client_id_clean or len(client_id_clean) < 3:
            raise ValueError("MELHOR_ENVIO_CLIENT_ID está vazio ou inválido. Verifique o .env")
        if not client_secret_clean or len(client_secret_clean) < 3:
            raise ValueError("MELHOR_ENVIO_CLIENT_SECRET está vazio ou inválido. Verifique o .env")
        
        response = self._make_oauth_request('POST', endpoint, data)
        
        # Valida resposta
        if 'access_token' not in response:
            raise ValueError(f"Resposta da API não contém access_token: {response}")
        if 'refresh_token' not in response:
            raise ValueError(f"Resposta da API não contém refresh_token: {response}")
        
        return Token(
            access_token=response['access_token'],
            refresh_token=response['refresh_token'],
            expires_in=response.get('expires_in', 2592000),  # 30 dias em segundos
            token_type=response.get('token_type', 'Bearer'),
            created_at=timezone.now()
        )
    
    def refresh_token(self, refresh_token: str) -> Token:
        """
        Renova um token de acesso usando o refresh_token
        
        Args:
            refresh_token: Token de renovação obtido na última requisição
            
        Returns:
            Token atualizado com novo access_token e refresh_token
        """
        endpoint = '/oauth/token'
        
        # OAuth usa form-urlencoded, não JSON
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token
        }
        
        response = self._make_oauth_request('POST', endpoint, data)
        
        return Token(
            access_token=response['access_token'],
            refresh_token=response['refresh_token'],
            expires_in=response.get('expires_in', 2592000),
            token_type=response.get('token_type', 'Bearer'),
            created_at=timezone.now()
        )
    
    def calculate_shipping(
        self,
        access_token: str,
        from_postal_code: str,
        to_postal_code: str,
        products: List[Dict],
        options: Optional[Dict] = None,
        services: Optional[str] = None
    ) -> List[ShippingQuote]:
        """
        Calcula frete baseado em produtos
        
        Args:
            access_token: Token de acesso autenticado
            from_postal_code: CEP de origem
            to_postal_code: CEP de destino
            products: Lista de produtos no formato do Melhor Envio
            options: Opções adicionais (receipt, own_hand, etc)
            services: IDs dos serviços separados por vírgula (opcional)
            
        Returns:
            Lista de cotações de frete
        """
        endpoint = '/api/v2/me/shipment/calculate'
        
        data = {
            'from': {
                'postal_code': from_postal_code
            },
            'to': {
                'postal_code': to_postal_code
            },
            'products': products
        }
        
        if options:
            data['options'] = options
        
        if services:
            data['services'] = services
        
        response = self._make_request('POST', endpoint, data, access_token)
        
        quotes = []
        for item in response:
            quotes.append(ShippingQuote(
                id=item.get('id'),
                name=item.get('name', ''),
                price=Decimal(str(item.get('price', 0))),
                delivery_time=item.get('delivery_time', 0),
                custom_price=Decimal(str(item['custom_price'])) if item.get('custom_price') else None,
                currency=item.get('currency', 'BRL'),
                custom_delivery_time=item.get('custom_delivery_time'),
                company=item.get('company', {})
            ))
        
        return quotes

