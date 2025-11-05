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

# Constante com imagem base64 mockada para item de frete
# Imagem PNG pequena de um ícone de caminhão/frete (pode ser substituída por uma imagem real)
# Para usar uma imagem real, substitua este valor por uma string base64 válida de uma imagem PNG/JPG
# Esta é uma imagem PNG de exemplo - substitua pela imagem desejada
SHIPPING_ITEM_IMAGE_BASE64 = (
    "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r1Fkvb6gH+cgaEfQi9tTKLYx9OIqBG4yPbgjhaIr+zM9uBqh6/ERW92dKbSB/ovY6q5B+HaqYiu7K4U2MaKWrexaJMH5bF13p9BGrmLruh6JUPI7tqZ7UmgrZdPYmm5AQrR/hq1nUgptp3w6W89NSIzOL7GV1P6mFG2p4nW2kprxJUiOillsFfP3QRvb4F22ig93RqL0eJGtYEovtLmNXmMreLAbEqb9HWyp1WcgCjo/ypZadiwS6NwatshbQxANJb9ky8wYiETafyFbYEInRMZRS1m4mivKkFC9Hmah5uyPKOk/jYX6665IsEMWsBBvjy5FxJy4hIWYeVAJEq3nzVVsrr8emkL0bHxvDZvrlR9CNp9Uw+b4y4EliKatH2WzvLgX5CvffqSGVi/viwgbOqWWVv+7G6Re37FzaPDGVTsi4jYb/yHdamddNgzyH4ZPnM+mLH/iJ/0QB6k9J33Gpix55Pg+kIZKvnPus6vZqDnX7dUB8ZHabuzzlWzUW1fv3g6yTp22HfXz+2d9VsU6q/4xbcJZBwxA/JRvd+SlD+YWVbPOyrlP35jZrz/EpHPv/xq29SbdyxB75X0GDft2/26lEBERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERkRj6F5cPg2vJIsc9AAAAAElFTkSuQmCC"
)


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
                
                # Busca informações do frete se existir e adiciona como último item
                from modules.pedido.adapters.persistence.models import OrderShipping as OrderShippingModel
                try:
                    shipping = OrderShippingModel.objects.get(order_id=order.id)
                    
                    # Monta o nome do frete incluindo service_name e name da company se disponível
                    shipping_company_name_parts = [shipping.company['name']]
                    if shipping.company and isinstance(shipping.company, dict) and shipping.company.get('name'):
                        shipping_company_name_parts.append(shipping.service_name)
                    
                    shipping_name = " ".join(shipping_company_name_parts)
                    
                    shipping_item = {
                        'name': f"Frete - {shipping_name}",
                        'value': float(shipping.final_price),
                        'quantity': 1,
                        'externalReference': f"SHIPPING_{shipping.service_id}",
                        'imageBase64': SHIPPING_ITEM_IMAGE_BASE64
                    }
                    checkout_items.append(shipping_item)
                except OrderShippingModel.DoesNotExist:
                    # Pedido sem frete, continua normalmente
                    pass
                
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
