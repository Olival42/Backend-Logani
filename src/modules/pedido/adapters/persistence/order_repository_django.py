from typing import Optional, List
from modules.pedido.domain.entities.order_entity import Order as OrderEntity, OrderItem as OrderItemEntity
from modules.pedido.adapters.persistence.models import Order as OrderModel, OrderItem as OrderItemModel
from modules.pedido.domain.repositories.order_repository import IOrderRepository
from modules.cliente.adapters.persistence.models import Client as ClientModel
from modules.cliente.adapters.persistence.client_repository_django import ClientRepository
from decimal import Decimal
import uuid


class OrderRepository(IOrderRepository):
    """Repositório Django para pedidos"""
    
    def __init__(self):
        self.client_repository = ClientRepository()
    
    def save(self, order: OrderEntity) -> OrderEntity:
        """Salva um pedido e seus itens"""
        # Busca cliente
        client_model = ClientModel.objects.get(id=order.client.id)
        
        # Cria o pedido
        order_model = OrderModel.objects.create(
            id=order.id,
            client=client_model,
            subtotal=order.subtotal,
            total=order.total,
            status=order.status,
            external_reference=order.external_reference,
            notes=order.notes,
            confirmed_at=order.confirmed_at
        )
        
        # Cria os itens
        for item in order.items:
            item_model = OrderItemModel.objects.create(
                id=uuid.uuid4(),  # Gera UUID único
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price
            )
            order_model.items.add(item_model)
        
        order.id = str(order_model.id)
        
        # Busca o pedido salvo com os itens relacionados para retornar entidade completa
        saved_order_model = OrderModel.objects.prefetch_related('items').get(id=order_model.id)
        return self._model_to_entity(saved_order_model)
    
    def get_by_id(self, order_id: str) -> Optional[OrderEntity]:
        """Busca um pedido por ID"""
        try:
            order_model = OrderModel.objects.prefetch_related('items').get(id=order_id)
            return self._model_to_entity(order_model)
        except OrderModel.DoesNotExist:
            return None
    
    def get_by_client(self, client_id: str) -> List[OrderEntity]:
        """Busca pedidos de um cliente"""
        order_models = OrderModel.objects.filter(client_id=client_id).prefetch_related('items')
        return [self._model_to_entity(model) for model in order_models]
    
    def get_by_external_reference(self, external_reference: str) -> Optional[OrderEntity]:
        """Busca um pedido por referência externa"""
        try:
            order_model = OrderModel.objects.prefetch_related('items').get(
                external_reference=external_reference
            )
            return self._model_to_entity(order_model)
        except OrderModel.DoesNotExist:
            return None
    
    def get_by_status(self, status: str) -> List[OrderEntity]:
        """Busca pedidos por status"""
        order_models = OrderModel.objects.filter(status=status).prefetch_related('items')
        return [self._model_to_entity(model) for model in order_models]
    
    def update(self, order: OrderEntity) -> OrderEntity:
        """Atualiza um pedido (incluindo itens)"""
        order_model = OrderModel.objects.get(id=order.id)
        
        # Limpa itens antigos
        order_model.items.clear()
        
        # Adiciona novos itens
        for item in order.items:
            item_model = OrderItemModel.objects.create(
                id=uuid.uuid4(),
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price
            )
            order_model.items.add(item_model)
        
        # Atualiza outros campos
        order_model.status = order.status
        order_model.confirmed_at = order.confirmed_at
        order_model.notes = order.notes
        order_model.subtotal = order.subtotal
        order_model.total = order.total
        
        order_model.save()
        
        # Busca o pedido atualizado com itens relacionados
        updated_order_model = OrderModel.objects.prefetch_related('items').get(id=order_model.id)
        return self._model_to_entity(updated_order_model)
    
    def list_all(self) -> List[OrderEntity]:
        """Lista todos os pedidos"""
        order_models = OrderModel.objects.all().prefetch_related('items')
        return [self._model_to_entity(model) for model in order_models]
    
    def _model_to_entity(self, model: OrderModel) -> OrderEntity:
        """Converte modelo Django para entidade"""
        from modules.cliente.domain.entities.client_entity import Client as ClientEntity
        from modules.cliente.domain.entities.address_entity import Address as AddressEntity
        
        # Converte cliente
        client_model = model.client
        address_model = client_model.address if hasattr(client_model, 'address') else None
        
        address_entity = None
        if address_model:
            address_entity = AddressEntity(
                address=address_model.address,
                number=address_model.address_number,
                postal_code=address_model.postal_code,
                city=address_model.city,
                state=address_model.state,
                complement=address_model.complement or '',
                province=address_model.province
            )
        
        # Obtém o email do usuário se existir
        client_email = None
        if client_model.user and hasattr(client_model.user, 'email'):
            client_email = client_model.user.email
        
        client_entity = ClientEntity(
            id=str(client_model.id),
            name=client_model.name,
            cpf=client_model.cpf,
            phone=client_model.phone or '',
            mobile_phone=client_model.mobile_phone or '',
            address=address_entity or AddressEntity('', '', '', '', '', '', ''),
            asaas_id=client_model.asaas_id,
            email=client_email
        )
        
        # Converte itens
        items = []
        for item_model in model.items.all():
            item = OrderItemEntity(
                product_id=item_model.product_id,
                product_name=item_model.product_name,
                quantity=item_model.quantity,
                unit_price=Decimal(str(item_model.unit_price)),
                total_price=Decimal(str(item_model.total_price))
            )
            items.append(item)
        
        return OrderEntity(
            id=str(model.id),
            client=client_entity,
            items=items,
            subtotal=Decimal(str(model.subtotal)),
            total=Decimal(str(model.total)),
            status=model.status,
            external_reference=model.external_reference,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
            confirmed_at=model.confirmed_at
        )

