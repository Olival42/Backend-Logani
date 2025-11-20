import requests
from typing import Dict, Any, List, Optional
from django.conf import settings
from modules.webhook.domain.entities.webhook_entity import Webhook


class AsaasWebhookClient:
    """
    Cliente para integração com a API de Webhooks do ASAAS
    Documentação: https://docs.asaas.com/reference/criar-novo-webhook
    """
    
    def __init__(self):
        self.api_url = settings.ASAAS_API_URL
        self.api_token = settings.ASAAS_API_TOKEN
        self.environment = settings.ASAAS_ENVIRONMENT
        
        if not self.api_token:
            raise ValueError("ASAAS_API_TOKEN não configurado nas variáveis de ambiente")
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna os headers padrão para requisições à API do Asaas"""
        return {
            'access_token': self.api_token,
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Realiza uma requisição HTTP para a API do Asaas"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
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
            error_detail = "Erro na API do Asaas"
            try:
                error_response = e.response.json()
                error_detail = error_response.get('errors', [{}])[0].get('description', error_detail)
            except (ValueError, KeyError, IndexError):
                pass
            
            raise ValueError(f"{error_detail} (Status: {e.response.status_code})")
        
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Erro de conexão com a API do Asaas: {str(e)}")
    
    def create_webhook(
        self,
        url: str,
        events: List[str],
        email: Optional[str] = None,
        api_version: str = 'v3',
        auth_token: Optional[str] = None,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Cria um novo webhook no Asaas
        
        Args:
            url: URL do webhook (obrigatório)
            events: Lista de eventos a serem notificados (obrigatório)
            email: Email para notificações (opcional)
            api_version: Versão da API (padrão: v3)
            auth_token: Token de autenticação (opcional)
            enabled: Webhook habilitado (padrão: True)
        
        Returns:
            Dict com a resposta da API
        """
        data = {
            'url': url,
            'events': events,
        }
        
        if email:
            data['email'] = email
        
        if api_version:
            data['apiVersion'] = api_version
        
        if auth_token:
            data['authToken'] = auth_token
        
        if enabled is not None:
            data['enabled'] = enabled
        
        try:
            response = self._make_request('POST', 'webhooks', data)
            return response
        except Exception as e:
            raise ValueError(f"Erro ao criar webhook no Asaas: {str(e)}")
    
    def update_webhook(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        email: Optional[str] = None,
        enabled: Optional[bool] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Atualiza um webhook existente no Asaas
        
        Args:
            webhook_id: ID do webhook no ASAAS
            url: Nova URL do webhook
            events: Nova lista de eventos
            email: Novo email
            enabled: Novo status de habilitação
            auth_token: Novo token de autenticação
        
        Returns:
            Dict com a resposta da API
        """
        data = {}
        
        if url:
            data['url'] = url
        
        if events is not None:
            data['events'] = events
        
        if email is not None:
            data['email'] = email
        
        if enabled is not None:
            data['enabled'] = enabled
        
        if auth_token is not None:
            data['authToken'] = auth_token
        
        if not data:
            raise ValueError("Nenhum campo para atualizar")
        
        try:
            response = self._make_request('PUT', f'webhooks/{webhook_id}', data)
            return response
        except Exception as e:
            raise ValueError(f"Erro ao atualizar webhook no Asaas: {str(e)}")
    
    def get_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Recupera um webhook do Asaas
        
        Args:
            webhook_id: ID do webhook
        
        Returns:
            Dict com os dados do webhook
        """
        try:
            response = self._make_request('GET', f'webhooks/{webhook_id}')
            return response
        except Exception as e:
            raise ValueError(f"Erro ao consultar webhook no Asaas: {str(e)}")
    
    def list_webhooks(self) -> Dict[str, Any]:
        """
        Lista todos os webhooks do Asaas
        
        Returns:
            Dict com a lista de webhooks
        """
        try:
            response = self._make_request('GET', 'webhooks')
            return response
        except Exception as e:
            raise ValueError(f"Erro ao listar webhooks no Asaas: {str(e)}")
    
    def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Remove um webhook do Asaas
        
        Args:
            webhook_id: ID do webhook
        
        Returns:
            Dict com a resposta da API
        """
        try:
            response = self._make_request('DELETE', f'webhooks/{webhook_id}')
            return response
        except Exception as e:
            raise ValueError(f"Erro ao remover webhook no Asaas: {str(e)}")

