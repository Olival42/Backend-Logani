import requests
import json
import time
import logging
from typing import Dict, Optional, Any, List
from django.conf import settings
from modules.checkout.domain.entities.checkout_entity import Checkout
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Singleton para sessão HTTP compartilhada (reutiliza conexões)
_shared_session = None


def get_shared_session():
    """Retorna uma sessão HTTP compartilhada com pool de conexões"""
    global _shared_session
    if _shared_session is None:
        _shared_session = requests.Session()
        
        # Configura retry automático
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )
        
        # Configura pool de conexões
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Número de pools de conexão
            pool_maxsize=20,      # Máximo de conexões por pool
            pool_block=False      # Não bloqueia se pool estiver cheio
        )
        
        _shared_session.mount("http://", adapter)
        _shared_session.mount("https://", adapter)
    
    return _shared_session


class AsaasCheckoutClient:
    """
    Cliente para integração com a API de Checkout do ASAAS
    """
    
    def __init__(self):
        self.api_url = settings.ASAAS_API_URL
        self.api_token = settings.ASAAS_API_TOKEN
        self.environment = settings.ASAAS_ENVIRONMENT
        
        if not self.api_token:
            raise ValueError("ASAAS_API_TOKEN não configurado nas variáveis de ambiente")
        
        # Usa sessão compartilhada para reutilizar conexões
        self.session = get_shared_session()
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna os headers padrão para requisições à API do Asaas"""
        return {
            'access_token': self.api_token,
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Realiza uma requisição HTTP para a API do Asaas
        
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint da API (sem a URL base)
            data: Dados para enviar no corpo da requisição
            
        Returns:
            Dict com a resposta da API
            
        Raises:
            requests.RequestException: Em caso de erro na requisição
            ValueError: Em caso de erro na resposta da API
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            timeout = 15  # Timeout de 15 segundos
            request_start = time.time()
            
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, timeout=timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == 'PUT':
                response = self.session.put(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
            
            request_time = (time.time() - request_start) * 1000
            logger.info(f"⏱️ [Asaas] {method} {endpoint}: {request_time:.2f}ms")
            
            response.raise_for_status()
            
            # Asaas retorna dados em diferentes formatos dependendo do endpoint
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
    
    def _convert_checkout_to_asaas_format(self, checkout: Checkout, items: Optional[List[Dict]] = None, walletId: str = None, paymentMethods: Optional[List[str]] = None, minutesToExpire: int = None, chargeTypes: Optional[List[str]] = None, installment: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Converte uma entidade Checkout para o formato esperado pela API do Asaas
        Baseado na documentação: https://docs.asaas.com/reference/criar-novo-checkout
        
        Args:
            checkout: Entidade Checkout
            items: Lista de itens do checkout
            walletId: ID da carteira (obrigatório)
            paymentMethods: Lista de métodos de pagamento permitidos (recebe como paymentMethods mas envia como billingTypes)
            minutesToExpire: Minutos até a expiração do checkout
            chargeTypes: Tipos de cobrança (DETACHED, RECURRENT, INSTALLMENT) - obrigatório
            
        Returns:
            Dict com os dados no formato do Asaas
        """
        from datetime import datetime, timedelta
        
        # Data de vencimento (obrigatória para o ASAAS)
        due_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        data = {
            'value': float(checkout.value),
            'customer': checkout.client.asaas_id,
            'dueDate': due_date
        }
        
        # Adiciona walletId (obrigatório)
        data['walletId'] = walletId
        
        # Adiciona chargeTypes (obrigatório)
        if chargeTypes:
            data['chargeTypes'] = chargeTypes
        else:
            # Padrão para tipo de cobrança
            data['chargeTypes'] = ['DETACHED']
        
        # Adiciona minutos de expiração se fornecido
        if minutesToExpire is not None:
            data['minutesToExpire'] = minutesToExpire
        
        # Adiciona itens se fornecidos
        if items:
            data['items'] = items
        
        # Campos opcionais conforme documentação ASAAS
        if checkout.description:
            data['description'] = checkout.description
        
        if checkout.external_reference:
            data['externalReference'] = checkout.external_reference
        
        # URLs de callback (ASAAS requer um objeto callback com todas as URLs)
        callback_data = {}
        if checkout.success_url:
            callback_data['successUrl'] = checkout.success_url
        
        if checkout.failure_url:
            # O ASAAS usa cancelUrl no objeto callback, não failureUrl
            callback_data['cancelUrl'] = checkout.failure_url
        
        if checkout.expires_url:
            callback_data['expiredUrl'] = checkout.expires_url
        
        # Adiciona o objeto callback apenas se houver pelo menos uma URL
        if callback_data:
            data['callback'] = callback_data
        
        # Configurações de pagamento
        if checkout.installments > 1:
            data['installments'] = checkout.installments
        
        # Adiciona configurações de parcelamento se fornecido (requerido quando INSTALLMENT está nos chargeTypes)
        if installment:
            data['installment'] = installment
        
        # Métodos de pagamento (ASAAS usa billingTypes) - obrigatório
        if paymentMethods:
            data['billingTypes'] = paymentMethods
        else:
            # Se não especificado, padrão é apenas CREDIT_CARD e BOLETO
            # PIX foi removido pois requer chave PIX cadastrada no ASAAS
            data['billingTypes'] = ['CREDIT_CARD', 'BOLETO']
        
        return data
    
    def create_checkout(self, checkout: Checkout, items: Optional[List[Dict]] = None, walletId: str = None, paymentMethods: Optional[List[str]] = None, minutesToExpire: int = None, chargeTypes: Optional[List[str]] = None, installment: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Cria um novo checkout no Asaas
        
        Args:
            checkout: Entidade Checkout
            items: Lista de itens do checkout
            walletId: ID da carteira (obrigatório)
            paymentMethods: Lista de métodos de pagamento permitidos
            minutesToExpire: Minutos até a expiração do checkout
            chargeTypes: Tipos de cobrança (DETACHED, RECURRENT, INSTALLMENT)
            
        Returns:
            Dict com a resposta da API contendo o ID do checkout criado
            
        Raises:
            ValueError: Em caso de erro na criação
        """
        data = self._convert_checkout_to_asaas_format(checkout, items, walletId, paymentMethods, minutesToExpire, chargeTypes, installment)
        
        try:
            response = self._make_request('POST', 'checkouts', data)
            return response
        except Exception as e:
            raise ValueError(f"Erro ao criar checkout no Asaas: {str(e)}")
    
    def get_checkout(self, asaas_checkout_id: str) -> Dict[str, Any]:
        """
        Recupera dados de um checkout do Asaas
        
        Args:
            asaas_checkout_id: ID do checkout no Asaas
            
        Returns:
            Dict com os dados do checkout
            
        Raises:
            ValueError: Em caso de erro na consulta
        """
        try:
            response = self._make_request('GET', f'checkouts/{asaas_checkout_id}')
            return response
        except Exception as e:
            raise ValueError(f"Erro ao consultar checkout no Asaas: {str(e)}")
    
    def cancel_checkout(self, asaas_checkout_id: str) -> Dict[str, Any]:
        """
        Cancela um checkout no Asaas
        
        Args:
            asaas_checkout_id: ID do checkout no Asaas
            
        Returns:
            Dict com a resposta da API
            
        Raises:
            ValueError: Em caso de erro no cancelamento
        """
        try:
            response = self._make_request('POST', f'checkouts/{asaas_checkout_id}/cancel')
            return response
        except Exception as e:
            raise ValueError(f"Erro ao cancelar checkout no Asaas: {str(e)}")
    
    def refund_payment(self, payment_id: str, value: Optional[float] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Solicita estorno de um pagamento no Asaas
        Documentação: https://docs.asaas.com/reference/estornar-pagamento
        
        Args:
            payment_id: ID do pagamento no Asaas (formato: pay_xxxxx)
            value: Valor a estornar (opcional, estorna tudo se não informado)
            description: Descrição do estorno (opcional)
            
        Returns:
            Dict com a resposta da API
            
        Raises:
            ValueError: Em caso de erro no estorno
        """
        try:
            data = {}
            
            if value is not None:
                data['value'] = float(value)
            
            if description:
                data['description'] = description
            
            # Endpoint correto para estorno é /payments/{id}/refund
            response = self._make_request('POST', f'payments/{payment_id}/refund', data if data else None)
            return response
        except Exception as e:
            raise ValueError(f"Erro ao estornar pagamento no Asaas: {str(e)}")