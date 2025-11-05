from rest_framework.views import APIView

from modules.checkout.application.web.serializers import (
    CreateCheckoutSerializer,
    CheckoutListSerializer,
    CheckoutDetailSerializer
)
from modules.checkout.domain.services.checkout_service import CheckoutService
from modules.checkout.adapters.persistence.checkout_repository_django import CheckoutRepository
from modules.usuario.domain.services import UserService
from modules.usuario.adapters.persistence.user_repository_django import UserRepository
from modules.usuario.adapters.persistence.blacklist_repository_django import BlacklistRepository
from api_pagamento_frete.utils import ErrorResponse, SuccessResponse, produto_repository


class CheckoutCreateView(APIView):
    """
    View para criar novos checkouts
    """
    
    def post(self, request):
        """
        Cria um novo checkout baseado na documentação ASAAS
        
        Opção 1: Checkout manual (informar value e items):
        {
            "value": 50.00,
            "customer": "cus_123456789",
            "chargeTypes": ["DETACHED"],
            "minutesToExpire": 60,
            "items": [
                {
                    "name": "Produto A",
                    "value": 25.00,
                    "quantity": 2,
                    "imageBase64": "base64..."
                }
            ]
        }
        
        Opção 2: Checkout baseado em pedido existente (só informar externalReference):
        {
            "externalReference": "ORD_20251101203654_0A38230E",
            "customer": "cus_123456789",
            "chargeTypes": ["DETACHED", "INSTALLMENT"],
            "minutesToExpire": 60,
            "callback": {
                "successUrl": "https://seusite.com/sucesso",
                "cancelUrl": "https://seusite.com/falha",
                "expiredUrl": "https://seusite.com/expirado"
            },
            "paymentMethods": ["PIX", "CREDIT_CARD"],
            "installment": {
                "maxInstallmentCount": 5
            }
        }
        """
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token não informado")

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return ErrorResponse.unauthorized(str(e))

        # Validação dos dados
        serializer = CreateCheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse.validation_error(serializer.errors)

        validated_data = serializer.validated_data.copy()
        
        # Se externalReference foi informado e não tem value/items, busca do pedido
        if validated_data.get('externalReference') and not validated_data.get('value'):
            from modules.pedido.adapters.persistence.order_repository_django import OrderRepository
            
            order_repository = OrderRepository()
            try:
                order = order_repository.get_by_external_reference(validated_data['externalReference'])
                
                if not order:
                    return ErrorResponse.bad_request(
                        f"Pedido com external_reference '{validated_data['externalReference']}' não encontrado"
                    )
                
                # Verifica se o pedido está ativo
                if not order.active:
                    return ErrorResponse.bad_request(
                        "Não é possível criar checkout para um pedido inativo"
                    )
                
                # Busca dados dos produtos e monta os itens
                checkout_items = []
                for item in order.items:
                    product = produto_repository.get_by_id(item.product_id)
                    if product:
                        item_data = {
                            'name': item.product_name,
                            'value': float(item.unit_price),
                            'quantity': item.quantity,
                            'externalReference': item.product_id  # ID do produto como externalReference
                        }
                        # Adiciona imagem se disponível
                        if product.imagem:
                            item_data['imageBase64'] = product.imagem
                        checkout_items.append(item_data)
                
                # Atualiza os dados validados com os valores do pedido
                validated_data['value'] = float(order.total)
                validated_data['items'] = checkout_items
                
                # Se não passou description, usa a do pedido
                if not validated_data.get('description'):
                    validated_data['description'] = f"Pagamento do pedido {validated_data['externalReference']}"
                    
            except Exception as e:
                return ErrorResponse.internal_server_error(
                    "Erro ao buscar dados do pedido",
                    details=str(e)
                )

        # Criação do checkout
        checkout_service = CheckoutService(CheckoutRepository())
        try:
            result = checkout_service.create_checkout(**validated_data)
            
            return SuccessResponse.created(
                data=result,
                message="Checkout criado com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class CheckoutDetailView(APIView):
    """
    View para consultar detalhes de um checkout
    """
    
    def get(self, request, checkout_id):
        """
        Consulta detalhes de um checkout
        
        Args:
            checkout_id: ID do checkout
        """
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token não informado")

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return ErrorResponse.unauthorized(str(e))

        # Busca o checkout
        checkout_service = CheckoutService(CheckoutRepository())
        try:
            checkout = checkout_service.get_checkout(checkout_id)
            
            if not checkout:
                return ErrorResponse.not_found("Checkout não encontrado")
            
            # Serializa os dados
            serializer = CheckoutDetailSerializer({
                'id': checkout.id,
                'asaas_id': checkout.asaas_id,
                'name': checkout.name,
                'description': checkout.description,
                'value': checkout.value,
                'status': checkout.status,
                'installments': checkout.installments,
                'checkout_url': checkout.checkout_url,
                'successUrl': checkout.success_url,
                'failureUrl': checkout.failure_url,
                'expiresUrl': checkout.expires_url,
                'externalReference': checkout.external_reference,
                'created_at': checkout.created_at,
                'updated_at': checkout.updated_at,
                'expires_at': checkout.expires_at,
                'client': {
                    'id': checkout.client.id,
                    'name': checkout.client.name,
                    'cpf': checkout.client.cpf,
                    'email': checkout.client.user.email if checkout.client.user else None
                }
            })
            
            return SuccessResponse.ok(
                data=serializer.data,
                message="Checkout encontrado"
            )
            
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class CheckoutCancelView(APIView):
    """
    View para cancelar um checkout
    """
    
    def post(self, request, checkout_id):
        """
        Cancela um checkout
        
        Args:
            checkout_id: ID do checkout
        """
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token não informado")

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return ErrorResponse.unauthorized(str(e))

        # Cancelamento do checkout
        checkout_service = CheckoutService(CheckoutRepository())
        try:
            result = checkout_service.cancel_checkout(checkout_id)
            
            return SuccessResponse.ok(
                data=result,
                message="Checkout cancelado com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class CheckoutSyncView(APIView):
    """
    View para sincronizar status de checkout com ASAAS
    """
    
    def post(self, request, checkout_id):
        """
        Sincroniza o status de um checkout com o ASAAS
        
        Args:
            checkout_id: ID do checkout
        """
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token não informado")

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return ErrorResponse.unauthorized(str(e))

        # Sincronização do checkout
        checkout_service = CheckoutService(CheckoutRepository())
        try:
            result = checkout_service.sync_checkout_status(checkout_id)
            
            return SuccessResponse.ok(
                data=result,
                message="Status do checkout sincronizado com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class CheckoutListView(APIView):
    """
    View para listar checkouts
    """
    
    def get(self, request):
        """
        Lista checkouts com filtros opcionais
        
        Query Parameters:
        - client_id: Filtrar por cliente
        - status: Filtrar por status
        - limit: Limite de resultados (padrão: 100)
        - offset: Offset para paginação (padrão: 0)
        """
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token não informado")

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return ErrorResponse.unauthorized(str(e))

        # Parâmetros de filtro
        client_id = request.query_params.get('client_id')
        status_filter = request.query_params.get('status')
        limit = int(request.query_params.get('limit', 100))
        offset = int(request.query_params.get('offset', 0))

        # Busca os checkouts
        checkout_service = CheckoutService(CheckoutRepository())
        try:
            if client_id:
                checkouts = checkout_service.get_client_checkouts(client_id)
            elif status_filter:
                checkouts = checkout_service.checkout_repository.get_by_status(status_filter)
            else:
                checkouts = checkout_service.checkout_repository.list_all(limit, offset)
            
            # Serializa os dados
            serializer = CheckoutListSerializer([
                {
                    'id': checkout.id,
                    'name': checkout.name,
                    'value': checkout.value,
                    'status': checkout.status,
                    'installments': checkout.installments,
                    'checkout_url': checkout.checkout_url,
                    'created_at': checkout.created_at,
                    'expires_at': checkout.expires_at,
                    'client': checkout.client
                }
                for checkout in checkouts
            ], many=True)
            
            return SuccessResponse.ok(
                data={
                    "checkouts": serializer.data,
                    "count": len(checkouts)
                },
                message=f"Encontrados {len(checkouts)} checkouts"
            )
            
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )
