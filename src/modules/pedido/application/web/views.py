from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from modules.pedido.application.web.serializers import (
    CreateOrderSerializer,
    OrderResponseSerializer,
    OrderDetailSerializer,
    UpdateOrderStatusSerializer
)
from modules.pedido.domain.services.order_service import OrderService
from modules.pedido.adapters.persistence.order_repository_django import OrderRepository
from modules.cliente.adapters.persistence.client_repository_django import ClientRepository
from modules.usuario.domain.services import UserService
from modules.usuario.adapters.persistence.user_repository_django import UserRepository
from modules.usuario.adapters.persistence.blacklist_repository_django import BlacklistRepository


class OrderCreateView(APIView):
    """View para criar novos pedidos"""
    
    def post(self, request):
        """Cria um novo pedido"""
        
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"detail": "Token não informado"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Validação dos dados
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Busca o cliente do usuário logado
        # Extrai o user_id do token
        try:
            payload = user_service.authenticate(token)
            user_id = payload.get('user_id')
            
            client_repository = ClientRepository()
            client = client_repository.get_by_user_id(str(user_id))
            
            if not client:
                return Response(
                    {"error": "Cliente não encontrado para o usuário"},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {"error": f"Erro ao buscar cliente: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Criação do pedido
        order_service = OrderService(OrderRepository())
        try:
            result = order_service.create_order(
                client=client,
                items=serializer.validated_data['items'],
                notes=serializer.validated_data.get('notes')
            )
            
            return Response(
                {
                    "message": "Pedido criado com sucesso",
                    "data": result
                },
                status=status.HTTP_201_CREATED
            )
            
        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Erro interno do servidor: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrderDetailView(APIView):
    """View para detalhes de um pedido"""
    
    def get(self, request, order_id):
        """Consulta detalhes de um pedido"""
        
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"detail": "Token não informado"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Busca o pedido
        order_service = OrderService(OrderRepository())
        try:
            order = order_service.get_order(order_id)
            
            if not order:
                return Response(
                    {"error": "Pedido não encontrado"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
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
            
            serializer = OrderDetailSerializer({
                'order_id': order.id,
                'external_reference': order.external_reference,
                'client': client_data,
                'items': items_data,
                'subtotal': float(order.subtotal),
                'total': float(order.total),
                'status': order.status,
                'notes': order.notes,
                'created_at': order.created_at,
                'updated_at': order.updated_at,
                'confirmed_at': order.confirmed_at
            })
            
            return Response(
                {
                    "message": "Pedido encontrado",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": f"Erro interno do servidor: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrderConfirmView(APIView):
    """View para confirmar um pedido"""
    
    def post(self, request, order_id):
        """Confirma um pedido (chamado via webhook quando pagamento confirmado)"""
        
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"detail": "Token não informado"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Confirma o pedido
        order_service = OrderService(OrderRepository())
        try:
            result = order_service.confirm_order(order_id)
            
            return Response(
                {
                    "message": "Pedido confirmado com sucesso",
                    "data": result
                },
                status=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Erro interno do servidor: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrderCancelView(APIView):
    """View para cancelar um pedido"""
    
    def post(self, request, order_id):
        """Cancela um pedido"""
        
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"detail": "Token não informado"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Cancela o pedido
        order_service = OrderService(OrderRepository())
        try:
            result = order_service.cancel_order(order_id)
            
            return Response(
                {
                    "message": "Pedido cancelado com sucesso",
                    "data": result
                },
                status=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Erro interno do servidor: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrderListByClientView(APIView):
    """View para listar pedidos do cliente"""
    
    def get(self, request):
        """Lista pedidos do cliente logado"""
        
        # Autenticação
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"detail": "Token não informado"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(" ")[1]
        user_service = UserService(UserRepository(), BlacklistRepository())
        
        try:
            user_service.authenticate(token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Busca cliente
        try:
            # Extrai o user_id do token
            payload = user_service.authenticate(token)
            user_id = payload.get('user_id')
            
            client_repository = ClientRepository()
            client = client_repository.get_by_user_id(str(user_id))
            
            if not client:
                return Response(
                    {"error": "Cliente não encontrado"},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {"error": f"Erro ao buscar cliente: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Lista pedidos
        order_service = OrderService(OrderRepository())
        try:
            orders = order_service.get_client_orders(str(client.id))
            
            # Serializa os dados
            data = []
            for order in orders:
                data.append({
                    'order_id': order.id,
                    'external_reference': order.external_reference,
                    'total': float(order.total),
                    'status': order.status,
                    'total_items': order.total_items(),
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                })
            
            return Response(
                {
                    "message": f"Encontrados {len(orders)} pedidos",
                    "data": data,
                    "count": len(orders)
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": f"Erro interno do servidor: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

