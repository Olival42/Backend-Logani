from typing import Dict, Any, Optional
from modules.cliente.domain.entities.client_entity import Client as ClientEntity
from modules.cliente.domain.entities.address_entity import Address as AddressEntity
from .client_service import ClientService
from modules.cliente.adapters.external.asaas_client import AsaasClient
from modules.cliente.adapters.persistence.client_repository_django import ClientRepository


class AsaasClientService:
    """
    Serviço que integra o gerenciamento de clientes locais com a API do Asaas
    """
    
    def __init__(self):
        self.asaas_client = AsaasClient()
        self.client_repository = ClientRepository()
        self.client_service = ClientService(self.client_repository)
    
    def create_client_with_asaas(self, data: dict, user_id: int) -> Dict[str, Any]:
        """
        Cria um cliente primeiro no Asaas e depois no servidor local
        
        Args:
            data: Dados do cliente
            user_id: ID do usuário
            
        Returns:
            Dict com informações do cliente criado
            
        Raises:
            ValueError: Em caso de erro na criação
        """
        asaas_id = None
        client_entity = None
        
        try:
            # Primeiro cria uma entidade temporária para enviar ao Asaas
            temp_client = self._create_temp_client_entity(data, user_id)
            
            # Cria primeiro no Asaas
            asaas_response = self.asaas_client.create_customer(temp_client)
            
            if 'id' not in asaas_response:
                raise ValueError("Asaas não retornou ID do cliente criado")
            
            asaas_id = asaas_response['id']
            
            # Adiciona o ID do Asaas aos dados
            data['asaas_id'] = asaas_id
            
            # Garante que o ID usado no local seja o mesmo enviado ao Asaas como externalReference
            data['id'] = temp_client.id
            
            # Agora cria no servidor local
            client_entity = self.client_service.create_client(data, user_id)
            
            return {
                'local_id': str(client_entity.id),
                'asaas_id': asaas_id,
                'name': client_entity.name,
                'cpf': client_entity.cpf,
                'asaas_response': asaas_response
            }
            
        except Exception as e:
            # Se houve erro no servidor local, remove o cliente do Asaas
            if asaas_id:
                try:
                    self.asaas_client.delete_customer(asaas_id)
                except:
                    pass  # Log do erro mas não falha a operação principal
            
            raise ValueError(f"Erro ao criar cliente: {str(e)}")
    
    def _create_temp_client_entity(self, data: dict, user_id: int) -> ClientEntity:
        """
        Cria uma entidade cliente temporária para enviar ao Asaas
        
        Args:
            data: Dados do cliente
            user_id: ID do usuário
            
        Returns:
            ClientEntity temporária
        """
        from modules.usuario.adapters.persistence.models import User
        from uuid import uuid4
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User não encontrado")

        address_data = data.get("address", {})
        address_entity = AddressEntity(
            address=address_data.get("address"),
            number=address_data.get("number"),
            postal_code=address_data.get("postal_code"),
            city=address_data.get("city"),
            state=address_data.get("state"),
            complement=address_data.get("complement", ""),
            province=address_data.get("province")
        )

        # Gera UUID se não foi fornecido, para usar como externalReference no ASAAS
        client_id = data.get("id") or str(uuid4())

        client_entity = ClientEntity(
            id=client_id,
            name=data["name"],
            cpf=data["cpf"],
            phone=data.get("phone"),
            mobile_phone=data["mobile_phone"],
            address=address_entity,
            user=user,
            asaas_id=data.get("asaas_id")
        )
        
        return client_entity
    
    def update_client_with_asaas(self, client_id: str, data: dict) -> Dict[str, Any]:
        """
        Atualiza um cliente primeiro no Asaas e depois no servidor local
        
        Args:
            client_id: ID do cliente local
            data: Dados atualizados
            
        Returns:
            Dict com informações do cliente atualizado
            
        Raises:
            ValueError: Em caso de erro na atualização
        """
        original_client = None
        asaas_response = None
        
        try:
            # Busca o cliente local original
            original_client = self.client_repository.get_by_id(client_id)
            if not original_client:
                raise ValueError("Cliente não encontrado")
            
            # Se tem ID do Asaas, atualiza primeiro lá
            if original_client.asaas_id:
                # Cria uma entidade temporária com os dados atualizados
                temp_client = self._create_temp_client_entity_from_existing(
                    original_client, data
                )
                
                # Atualiza primeiro no Asaas
                asaas_response = self.asaas_client.update_customer(
                    original_client.asaas_id, 
                    temp_client
                )
                
                # Adiciona o ID do Asaas aos dados para manter consistência
                data['asaas_id'] = original_client.asaas_id
                
                # Agora atualiza no servidor local
                updated_client = self.client_service.update_client(client_id, data)
                
                return {
                    'local_id': str(updated_client.id),
                    'asaas_id': updated_client.asaas_id,
                    'name': updated_client.name,
                    'cpf': updated_client.cpf,
                    'asaas_response': asaas_response
                }
            else:
                # Se não tem ID do Asaas, atualiza apenas localmente
                updated_client = self.client_service.update_client(client_id, data)
                
                return {
                    'local_id': str(updated_client.id),
                    'asaas_id': None,
                    'name': updated_client.name,
                    'cpf': updated_client.cpf,
                    'message': 'Cliente atualizado localmente (não sincronizado com Asaas)'
                }
                
        except Exception as e:
            # Se houve erro no servidor local e já atualizou no Asaas,
            # tenta reverter a atualização no Asaas
            if asaas_response and original_client and original_client.asaas_id:
                try:
                    # Reverte para os dados originais no Asaas
                    self.asaas_client.update_customer(
                        original_client.asaas_id, 
                        original_client
                    )
                except:
                    pass  # Log do erro mas não falha a operação principal
            
            raise ValueError(f"Erro ao atualizar cliente: {str(e)}")
    
    def _create_temp_client_entity_from_existing(self, existing_client: ClientEntity, data: dict) -> ClientEntity:
        """
        Cria uma entidade cliente temporária baseada em um cliente existente com dados atualizados
        
        Args:
            existing_client: Cliente existente
            data: Dados atualizados
            
        Returns:
            ClientEntity temporária com dados atualizados
        """
        # Atualiza endereço se fornecido
        if "address" in data:
            address_data = data["address"]
            updated_address = AddressEntity(
                address=address_data.get("address", existing_client.address.address),
                number=address_data.get("number", existing_client.address.number),
                postal_code=address_data.get("postal_code", existing_client.address.postal_code),
                city=address_data.get("city", existing_client.address.city),
                state=address_data.get("state", existing_client.address.state),
                complement=address_data.get("complement", existing_client.address.complement),
                province=address_data.get("province", existing_client.address.province),
            )
        else:
            updated_address = existing_client.address

        # Cria nova entidade com dados atualizados
        updated_client = ClientEntity(
            id=existing_client.id,
            name=data.get("name", existing_client.name),
            cpf=data.get("cpf", existing_client.cpf),
            phone=data.get("phone", existing_client.phone),
            mobile_phone=data.get("mobile_phone", existing_client.mobile_phone),
            address=updated_address,
            user=existing_client.user,
            asaas_id=data.get("asaas_id", existing_client.asaas_id)
        )
        
        return updated_client
    
    def sync_client_to_asaas(self, client_id: str) -> Dict[str, Any]:
        """
        Sincroniza um cliente local existente com o Asaas
        
        Args:
            client_id: ID do cliente local
            
        Returns:
            Dict com informações da sincronização
            
        Raises:
            ValueError: Em caso de erro na sincronização
        """
        try:
            # Busca o cliente local
            client_entity = self.client_repository.get_by_id(client_id)
            if not client_entity:
                raise ValueError("Cliente não encontrado")
            
            # Se já tem ID do Asaas, atualiza
            if client_entity.asaas_id:
                asaas_response = self.asaas_client.update_customer(
                    client_entity.asaas_id, 
                    client_entity
                )
                action = 'updated'
            else:
                # Se não tem ID do Asaas, cria
                asaas_response = self.asaas_client.create_customer(client_entity)
                client_entity.asaas_id = asaas_response.get('id')
                self.client_repository.save(client_entity)
                action = 'created'
            
            return {
                'local_id': str(client_entity.id),
                'asaas_id': asaas_response.get('id'),
                'action': action,
                'asaas_response': asaas_response
            }
            
        except Exception as e:
            raise ValueError(f"Erro ao sincronizar cliente: {str(e)}")
    
    def get_client_from_asaas_by_local_id(self, local_client_id: str) -> Dict[str, Any]:
        """
        Busca dados de um cliente do Asaas usando o ID local do cliente
        
        Args:
            local_client_id: ID do cliente no sistema local
            
        Returns:
            Dict com os dados do cliente do Asaas
            
        Raises:
            ValueError: Em caso de erro na consulta
        """
        try:
            # Primeiro busca o cliente local para obter o asaas_id
            local_client = self.client_repository.get_by_id(local_client_id)
            if not local_client:
                raise ValueError("Cliente não encontrado no sistema local")
            
            if not local_client.asaas_id:
                raise ValueError("Cliente não está sincronizado com o Asaas")
            
            # Agora busca no Asaas usando o asaas_id
            asaas_response = self.asaas_client.get_customer(local_client.asaas_id)
            return {
                'local_id': local_client_id,
                'asaas_id': local_client.asaas_id,
                'asaas_data': asaas_response
            }
        except Exception as e:
            raise ValueError(f"Erro ao consultar cliente no Asaas: {str(e)}")
    
    def get_client_from_asaas(self, asaas_id: str) -> Dict[str, Any]:
        """
        Busca dados de um cliente diretamente do Asaas
        
        Args:
            asaas_id: ID do cliente no Asaas
            
        Returns:
            Dict com os dados do cliente do Asaas
            
        Raises:
            ValueError: Em caso de erro na consulta
        """
        try:
            asaas_response = self.asaas_client.get_customer(asaas_id)
            return {
                'asaas_id': asaas_id,
                'asaas_data': asaas_response
            }
        except Exception as e:
            raise ValueError(f"Erro ao consultar cliente no Asaas: {str(e)}")
