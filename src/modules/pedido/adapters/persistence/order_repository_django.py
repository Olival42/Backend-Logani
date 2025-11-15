from typing import Optional, List
from modules.pedido.domain.entities.order_entity import (
    Order as OrderEntity,
    OrderItem as OrderItemEntity,
    OrderShipping as OrderShippingEntity
)
from modules.pedido.adapters.persistence.models import (
    Order as OrderModel,
    OrderItem as OrderItemModel,
    OrderShipping as OrderShippingModel
)
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
            confirmed_at=order.confirmed_at,
            active=order.active
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
        """Busca um pedido por ID (apenas se estiver ativo)"""
        try:
            order_model = OrderModel.objects.prefetch_related('items').get(id=order_id, active=True)
            return self._model_to_entity(order_model)
        except OrderModel.DoesNotExist:
            return None
    
    def get_by_client(self, client_id: str) -> List[OrderEntity]:
        """Busca pedidos ativos de um cliente"""
        order_models = OrderModel.objects.filter(client_id=client_id, active=True).prefetch_related('items')
        return [self._model_to_entity(model) for model in order_models]
    
    def get_by_external_reference(self, external_reference: str, include_inactive: bool = False) -> Optional[OrderEntity]:
        """
        Busca um pedido por referência externa
        
        Args:
            external_reference: Referência externa do pedido
            include_inactive: Se True, busca mesmo se inativo (útil para webhooks)
        """
        try:
            query = OrderModel.objects.prefetch_related('items').filter(
                external_reference=external_reference
            )
            if not include_inactive:
                query = query.filter(active=True)
            order_model = query.get()
            return self._model_to_entity(order_model)
        except OrderModel.DoesNotExist:
            return None
    
    def get_by_status(self, status: str) -> List[OrderEntity]:
        """Busca pedidos ativos por status"""
        order_models = OrderModel.objects.filter(status=status, active=True).prefetch_related('items')
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
        order_model.active = order.active
        
        order_model.save()
        
        # Busca o pedido atualizado com itens relacionados
        updated_order_model = OrderModel.objects.prefetch_related('items').get(id=order_model.id)
        return self._model_to_entity(updated_order_model)
    
    def list_all(self) -> List[OrderEntity]:
        """Lista todos os pedidos ativos"""
        order_models = OrderModel.objects.filter(active=True).prefetch_related('items')
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
        user_model = getattr(client_model, 'user', None)
        client_email = user_model.email if user_model and hasattr(user_model, 'email') else None
        
        client_entity = ClientEntity(
            id=str(client_model.id),
            name=client_model.name,
            cpf=client_model.cpf,
            phone=client_model.phone or '',
            mobile_phone=client_model.mobile_phone or '',
            address=address_entity or AddressEntity('', '', '', '', '', '', ''),
            user=user_model,
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
        
        shipping_entity = None
        try:
            shipping_model = model.shipping
        except OrderShippingModel.DoesNotExist:
            shipping_model = None

        if shipping_model:
            shipping_entity = OrderShippingEntity(
                service_id=shipping_model.service_id,
                service_name=shipping_model.service_name,
                price=Decimal(str(shipping_model.price)),
                custom_price=Decimal(str(shipping_model.custom_price)) if shipping_model.custom_price is not None else None,
                delivery_time=shipping_model.delivery_time,
                custom_delivery_time=shipping_model.custom_delivery_time,
                currency=shipping_model.currency,
                company=shipping_model.company or {},
                from_postal_code=shipping_model.from_postal_code,
                to_postal_code=shipping_model.to_postal_code
            )

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
            confirmed_at=model.confirmed_at,
            active=model.active,
            shipping=shipping_entity
        )

