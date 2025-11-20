import requests
import json
from typing import Dict, Optional, Any
from django.conf import settings
from modules.cliente.domain.entities.client_entity import Client as ClientEntity
from modules.cliente.domain.entities.address_entity import Address as AddressEntity


class AsaasClient:
    """
    Cliente para integração com a API do Asaas
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
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
            
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
    
    def _convert_client_to_asaas_format(self, client: ClientEntity) -> Dict[str, Any]:
        """
        Converte uma entidade Client para o formato esperado pela API do Asaas
        
        Args:
            client: Entidade Client
            
        Returns:
            Dict com os dados no formato do Asaas
        """
        data = {
            'name': client.name,
            'cpfCnpj': client.cpf,
            'phone': client.phone,
            'mobilePhone': client.mobile_phone,
        }
        
        # Adiciona externalReference com o UUID do cliente
        if client.id:
            data['externalReference'] = str(client.id)
        
        # Adiciona email do usuário associado
        if client.user and hasattr(client.user, 'email'):
            data['email'] = client.user.email
        
        # Adiciona dados do endereço se disponível
        if client.address:
            address_data = {
                'address': client.address.address,
                'addressNumber': client.address.number,
                'complement': client.address.complement or '',
                'province': client.address.province,
                'city': client.address.city,
                'state': client.address.state,
                'postalCode': client.address.postal_code,
            }
            data.update(address_data)
        
        return data
    
    def create_customer(self, client: ClientEntity) -> Dict[str, Any]:
        """
        Cria um novo cliente no Asaas
        
        Args:
            client: Entidade Client
            
        Returns:
            Dict com a resposta da API contendo o ID do cliente criado
            
        Raises:
            ValueError: Em caso de erro na criação
        """
        data = self._convert_client_to_asaas_format(client)
        
        try:
            response = self._make_request('POST', 'customers', data)
            return response
        except Exception as e:
            raise ValueError(f"Erro ao criar cliente no Asaas: {str(e)}")
    
    def update_customer(self, asaas_id: str, client: ClientEntity) -> Dict[str, Any]:
        """
        Atualiza um cliente existente no Asaas
        
        Args:
            asaas_id: ID do cliente no Asaas
            client: Entidade Client com os dados atualizados
            
        Returns:
            Dict com a resposta da API
            
        Raises:
            ValueError: Em caso de erro na atualização
        """
        data = self._convert_client_to_asaas_format(client)
        
        try:
            response = self._make_request('PUT', f'customers/{asaas_id}', data)
            return response
        except Exception as e:
            raise ValueError(f"Erro ao atualizar cliente no Asaas: {str(e)}")
    
    def get_customer(self, asaas_id: str) -> Dict[str, Any]:
        """
        Recupera dados de um cliente do Asaas
        
        Args:
            asaas_id: ID do cliente no Asaas
            
        Returns:
            Dict com os dados do cliente
            
        Raises:
            ValueError: Em caso de erro na consulta
        """
        try:
            response = self._make_request('GET', f'customers/{asaas_id}')
            return response
        except Exception as e:
            raise ValueError(f"Erro ao consultar cliente no Asaas: {str(e)}")
    
    def refund_payment(self, payment_id: str, value: Optional[float] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Estorna um pagamento no Asaas
        Documentação: https://docs.asaas.com/reference/estornar-cobranca
        
        Args:
            payment_id: ID do pagamento no Asaas
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
            
            # Endpoint para estornar cobrança
            response = self._make_request('POST', f'payments/{payment_id}/refund', data if data else None)
            return response
        except Exception as e:
            raise ValueError(f"Erro ao estornar pagamento no Asaas: {str(e)}")
    
    def refund_installment(self, installment_id: str, value: Optional[float] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Estorna um parcelamento no Asaas
        Documentação: https://docs.asaas.com/reference/estornar-parcelamento
        
        Args:
            installment_id: ID do parcelamento no Asaas
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
            
            # Endpoint para estornar parcelamento
            response = self._make_request('POST', f'installments/{installment_id}/refund', data if data else None)
            return response
        except Exception as e:
            raise ValueError(f"Erro ao estornar parcelamento no Asaas: {str(e)}")