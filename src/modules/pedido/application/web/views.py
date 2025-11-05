from rest_framework.views import APIView
from django.db import DatabaseError, IntegrityError

from modules.pedido.application.web.serializers import (
    CreateOrderSerializer,
    OrderDetailSerializer,
    UpdateOrderSerializer,
    AddShippingToOrderSerializer,
)
from modules.pedido.domain.services.order_service import OrderService
from modules.pedido.adapters.persistence.order_repository_django import OrderRepository
from modules.cliente.adapters.persistence.client_repository_django import ClientRepository
from modules.usuario.domain.services import UserService
from modules.usuario.adapters.persistence.user_repository_django import UserRepository
from modules.usuario.adapters.persistence.blacklist_repository_django import BlacklistRepository
from api_pagamento_frete.utils import ErrorResponse, SuccessResponse, produto_repository


class OrderCreateView(APIView):
    """View para criar novos pedidos"""
    
    def post(self, request):
        """Cria um novo pedido"""
        
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
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse.validation_error(serializer.errors)
        
        # Busca o cliente do usuário logado
        # Extrai o user_id do token
        try:
            payload = user_service.authenticate(token)
            user_id = payload.get('user_id')
            
            client_repository = ClientRepository()
            client = client_repository.get_by_user_id(str(user_id))
            
            if not client:
                return ErrorResponse.not_found("Cliente não encontrado para o usuário")
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro ao buscar cliente", 
                details=str(e)
            )
        
        # Busca dados dos produtos pelos IDs
        items_with_product_data = []
        
        for item in serializer.validated_data['items']:
            product_id = item['product_id']
            quantity = item['quantity']
            
            # Busca o produto
            product = produto_repository.get_by_id(product_id)
            
            if not product:
                return ErrorResponse.bad_request(
                    f"Produto com ID '{product_id}' não encontrado"
                )
            
            # Monta o item com todos os dados do produto
            items_with_product_data.append({
                'product_id': product.id,
                'product_name': product.nome,
                'quantity': quantity,
                'unit_price': float(product.preco)
            })
        
        # Criação do pedido
        order_service = OrderService(OrderRepository())
        try:
            result = order_service.create_order(
                client=client,
                items=items_with_product_data,
                notes=serializer.validated_data.get('notes')
            )
            
            return SuccessResponse.created(
                data=result,
                message="Pedido criado com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except (DatabaseError, IntegrityError) as e:
            # Erro específico de banco de dados (constraints, transações, etc)
            return ErrorResponse.internal_server_error(
                "Erro ao salvar pedido no banco de dados", 
                details=str(e)
            )
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class OrderDetailView(APIView):
    """View para detalhes de um pedido"""
    
    def get(self, request, order_id):
        """Consulta detalhes de um pedido"""
        
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
        
        # Busca o pedido (apenas ativos - filtrado automaticamente pelo repositório)
        order_service = OrderService(OrderRepository())
        try:
            order = order_service.get_order(order_id)
            
            if not order:
                return ErrorResponse.not_found("Pedido não encontrado ou inativo")
            
            # Prepara dados do cliente (apenas id e name)
            client_data = {
                'id': order.client.id,
                'name': order.client.name
            }
            
            # Prepara itens do pedido
            items_data = [
                {
                    'product_id': item.product_id,
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                    'total_price': float(item.total_price)
                }
                for item in order.items
            ]
            
            # Busca informações do frete se existir
            shipping_data = None
            shipping_price = None
            from modules.pedido.adapters.persistence.models import OrderShipping as OrderShippingModel
            try:
                shipping = OrderShippingModel.objects.get(order_id=order.id)
                shipping_data = {
                    'service_id': shipping.service_id,
                    'service_name': shipping.service_name,
                    'price': float(shipping.price),
                    'custom_price': float(shipping.custom_price) if shipping.custom_price else None,
                    'final_price': float(shipping.final_price),
                    'delivery_time': shipping.delivery_time,
                    'custom_delivery_time': shipping.custom_delivery_time,
                    'final_delivery_time': shipping.final_delivery_time,
                    'currency': shipping.currency,
                    'company': shipping.company,
                    'from_postal_code': shipping.from_postal_code,
                    'to_postal_code': shipping.to_postal_code
                }
                shipping_price = float(shipping.final_price)
            except OrderShippingModel.DoesNotExist:
                pass
            
            serializer = OrderDetailSerializer({
                'order_id': order.id,
                'external_reference': order.external_reference,
                'client': client_data,
                'items': items_data,
                'subtotal': float(order.subtotal),
                'shipping': shipping_data,
                'shipping_price': shipping_price,
                'total': float(order.total),
                'status': order.status,
                'active': order.active,
                'notes': order.notes,
                'created_at': order.created_at,
                'updated_at': order.updated_at,
                'confirmed_at': order.confirmed_at
            })
            
            return SuccessResponse.ok(
                data=serializer.data,
                message="Pedido encontrado"
            )
            
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class OrderConfirmView(APIView):
    """View para confirmar um pedido"""
    
    def post(self, request, order_id):
        """Confirma um pedido (chamado via webhook quando pagamento confirmado)"""
        
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
        
        # Confirma o pedido
        order_service = OrderService(OrderRepository())
        try:
            result = order_service.confirm_order(order_id)
            
            return SuccessResponse.ok(
                data=result,
                message="Pedido confirmado com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class OrderCancelView(APIView):
    """View para cancelar um pedido"""
    
    def post(self, request, order_id):
        """Cancela um pedido"""
        
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
        
        # Cancela o pedido
        order_service = OrderService(OrderRepository())
        try:
            result = order_service.cancel_order(order_id)
            
            return SuccessResponse.ok(
                data=result,
                message="Pedido cancelado com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class OrderListByClientView(APIView):
    """View para listar pedidos do cliente"""
    
    def get(self, request):
        """Lista pedidos do cliente logado"""
        
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
        
        # Busca cliente
        try:
            # Extrai o user_id do token
            payload = user_service.authenticate(token)
            user_id = payload.get('user_id')
            
            client_repository = ClientRepository()
            client = client_repository.get_by_user_id(str(user_id))
            
            if not client:
                return ErrorResponse.not_found("Cliente não encontrado")
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro ao buscar cliente", 
                details=str(e)
            )
        
        # Parâmetros de filtro opcionais
        status_filter = request.query_params.get('status')  # Filtro opcional por status
        exclude_cancelled = request.query_params.get('exclude_cancelled', 'false').lower() == 'true'  # Excluir cancelados
        include_all_cancelled = request.query_params.get('include_all_cancelled', 'false').lower() == 'true'  # Incluir todos os cancelados (mesmo sem confirmação)
        
        # Lista pedidos
        order_service = OrderService(OrderRepository())
        try:
            orders = order_service.get_client_orders(str(client.id))
            
            # Por padrão, exclui pedidos cancelados que nunca foram confirmados/pagos
            # (pedidos que foram cancelados porque o checkout falhou antes do pagamento)
            if not include_all_cancelled:
                orders = [
                    order for order in orders 
                    if order.status != 'CANCELLED' 
                    or order.confirmed_at is not None  # Só mostra cancelados se foram confirmados antes
                    or order.status == 'PAID'  # Se estava pago antes de cancelar
                ]
            
            # Aplica filtros adicionais se fornecidos
            if status_filter:
                orders = [order for order in orders if order.status == status_filter.upper()]
            
            if exclude_cancelled:
                orders = [order for order in orders if order.status != 'CANCELLED']
            
            # Serializa os dados
            from modules.pedido.adapters.persistence.models import OrderShipping as OrderShippingModel
            data = []
            for order in orders:
                # Prepara itens do pedido
                items_data = [
                    {
                        'product_id': item.product_id,
                        'product_name': item.product_name,
                        'quantity': item.quantity,
                        'unit_price': float(item.unit_price),
                        'total_price': float(item.total_price)
                    }
                    for item in order.items
                ]
                
                # Busca informações do frete se existir
                shipping_data = None
                shipping_price = None
                try:
                    shipping = OrderShippingModel.objects.get(order_id=order.id)
                    shipping_data = {
                        'service_id': shipping.service_id,
                        'service_name': shipping.service_name,
                        'price': float(shipping.price),
                        'final_price': float(shipping.final_price),
                        'delivery_time': shipping.final_delivery_time,
                    }
                    shipping_price = float(shipping.final_price)
                except OrderShippingModel.DoesNotExist:
                    pass
                
                data.append({
                    'order_id': order.id,
                    'external_reference': order.external_reference,
                    'total': float(order.total),
                    'subtotal': float(order.subtotal),
                    'shipping': shipping_data,
                    'shipping_price': shipping_price,
                    'status': order.status,
                    'active': order.active,
                    'total_items': order.total_items(),
                    'items': items_data,
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'updated_at': order.updated_at.isoformat() if order.updated_at else None,
                    'confirmed_at': order.confirmed_at.isoformat() if order.confirmed_at else None,
                })
            
            return SuccessResponse.ok(
                data={
                    "orders": data,
                    "count": len(orders),
                    "filters_applied": {
                        "status": status_filter,
                        "exclude_cancelled": exclude_cancelled
                    }
                },
                message=f"Encontrados {len(orders)} pedidos"
            )
            
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class OrderUpdateView(APIView):
    """View para atualizar itens de um pedido"""
    
    def patch(self, request, order_id):
        """Atualiza itens de um pedido"""
        
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
        serializer = UpdateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse.validation_error(serializer.errors)
        
        # Atualização do pedido
        order_service = OrderService(OrderRepository())
        try:
            result = order_service.update_order_items(
                order_id=order_id,
                items_actions=serializer.validated_data['items'],
                produto_repository=produto_repository
            )
            
            return SuccessResponse.ok(
                data=result,
                message="Pedido atualizado com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except (DatabaseError, IntegrityError) as e:
            return ErrorResponse.internal_server_error(
                "Erro ao atualizar pedido no banco de dados", 
                details=str(e)
            )
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )


class OrderAddShippingView(APIView):
    """View para adicionar serviço de frete ao pedido"""
    
    def post(self, request, order_id):
        """Adiciona um serviço de frete ao pedido"""
        
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
        serializer = AddShippingToOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse.validation_error(serializer.errors)
        
        # Busca o pedido para obter o cliente e CEP de destino
        order_service = OrderService(OrderRepository())
        try:
            order = order_service.get_order(order_id)
            if not order:
                return ErrorResponse.not_found("Pedido não encontrado ou inativo")
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro ao buscar pedido",
                details=str(e)
            )
        
        # Busca o CEP de destino do endereço do cliente
        if not order.client.address or not order.client.address.postal_code:
            return ErrorResponse.bad_request(
                "Cliente do pedido não possui endereço com CEP cadastrado. Por favor, atualize o endereço do cliente."
            )
        
        to_postal_code = ''.join(filter(str.isdigit, order.client.address.postal_code))
        if len(to_postal_code) != 8:
            return ErrorResponse.bad_request(
                f"CEP do cliente é inválido. Deve ter 8 dígitos. CEP encontrado: {to_postal_code[:10]}..."
            )
        
        # Obtém CEP de origem: usa o enviado ou o do .env
        validated_data = serializer.validated_data.copy()
        from_postal_code = validated_data.get('from_postal_code')
        if not from_postal_code:
            from django.conf import settings
            from_postal_code = getattr(settings, 'OWNER_CEP', None)
            if not from_postal_code:
                return ErrorResponse.bad_request(
                    "CEP de origem não informado. Configure OWNER_CEP no .env ou envie from_postal_code na requisição."
                )
            # Remove formatação do CEP do .env
            from_postal_code = ''.join(filter(str.isdigit, str(from_postal_code)))
            if len(from_postal_code) != 8:
                return ErrorResponse.bad_request(
                    f"CEP de origem no .env (OWNER_CEP) é inválido. Deve ter 8 dígitos. Valor encontrado: {from_postal_code[:10]}..."
                )
        
        validated_data['from_postal_code'] = from_postal_code
        validated_data['to_postal_code'] = to_postal_code
        
        # Adiciona o frete ao pedido
        try:
            result = order_service.add_shipping_to_order(
                order_id=order_id,
                shipping_data=validated_data
            )
            
            return SuccessResponse.ok(
                data=result,
                message="Frete adicionado ao pedido com sucesso"
            )
            
        except ValueError as e:
            return ErrorResponse.bad_request(str(e))
        except (DatabaseError, IntegrityError) as e:
            return ErrorResponse.internal_server_error(
                "Erro ao adicionar frete ao pedido no banco de dados", 
                details=str(e)
            )
        except Exception as e:
            return ErrorResponse.internal_server_error(
                "Erro interno do servidor", 
                details=str(e)
            )

