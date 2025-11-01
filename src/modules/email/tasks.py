"""
Tasks Celery para envio de emails assíncronos
"""

from celery import shared_task
from celery.exceptions import Retry
from typing import List, Dict, Any
import json
import traceback


@shared_task(name='send_order_cancelled_email', bind=True, max_retries=3, default_retry_delay=60)
def send_order_cancelled_email_async(self, order_data: Dict[str, Any], client_data: Dict[str, Any], refund_info: List[Dict] = None) -> bool:
    """
    Task assíncrona para enviar email de pedido cancelado ao proprietário
    
    Args:
        self: Referência à task (usado para retry)
        order_data: Dados serializados do pedido
        client_data: Dados serializados do cliente
        refund_info: Lista com informações de estorno
        
    Returns:
        bool: True se o email foi enviado com sucesso
    """
    try:
        from modules.email.domain.services.email_service import EmailService
        from modules.pedido.domain.entities.order_entity import Order, OrderItem
        from modules.cliente.domain.entities.client_entity import Client
        from modules.cliente.domain.entities.address_entity import Address
        from decimal import Decimal
        from datetime import datetime, timezone
        
        # Converte os dados serializados de volta para entidades
        client = _deserialize_client(client_data)
        order = _deserialize_order(order_data, client)
        
        # Envia o email
        email_service = EmailService()
        result = email_service.send_order_cancelled_email(order, client, refund_info)
        
        if not result:
            # Se o email não foi enviado, tenta novamente
            raise ValueError("Email não foi enviado com sucesso")
        
        return result
        
    except Exception as e:
        # Registra o erro completo
        traceback.print_exc()
        
        # Tenta novamente se não atingiu o máximo de tentativas
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        else:
            return False


@shared_task(name='send_order_cancelled_email_to_customer', bind=True, max_retries=3, default_retry_delay=60)
def send_order_cancelled_email_to_customer_async(self, order_data: Dict[str, Any], client_data: Dict[str, Any]) -> bool:
    """
    Task assíncrona para enviar email de pedido cancelado ao cliente
    
    Args:
        self: Referência à task (usado para retry)
        order_data: Dados serializados do pedido
        client_data: Dados serializados do cliente
        
    Returns:
        bool: True se o email foi enviado com sucesso
    """
    try:
        from modules.email.domain.services.email_service import EmailService
        from modules.pedido.domain.entities.order_entity import Order, OrderItem
        from modules.cliente.domain.entities.client_entity import Client
        from modules.cliente.domain.entities.address_entity import Address
        from decimal import Decimal
        from datetime import datetime, timezone
        
        # Converte os dados serializados de volta para entidades
        client = _deserialize_client(client_data)
        order = _deserialize_order(order_data, client)
        
        # Envia o email
        email_service = EmailService()
        result = email_service.send_order_cancelled_email_to_customer(order, client)
        
        if not result:
            # Se o email não foi enviado, tenta novamente
            raise ValueError("Email não foi enviado com sucesso")
        
        return result
        
    except Exception as e:
        # Registra o erro completo
        traceback.print_exc()
        
        # Tenta novamente se não atingiu o máximo de tentativas
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        else:
            return False


@shared_task(name='send_refund_notification_email_to_customer', bind=True, max_retries=3, default_retry_delay=60)
def send_refund_notification_email_to_customer_async(self, order_data: Dict[str, Any], client_data: Dict[str, Any], payment_info: Dict = None) -> bool:
    """
    Task assíncrona para enviar email de estorno ao cliente
    
    Args:
        self: Referência à task (usado para retry)
        order_data: Dados serializados do pedido
        client_data: Dados serializados do cliente
        payment_info: Informações sobre o pagamento estornado
        
    Returns:
        bool: True se o email foi enviado com sucesso
    """
    try:
        from modules.email.domain.services.email_service import EmailService
        from modules.pedido.domain.entities.order_entity import Order, OrderItem
        from modules.cliente.domain.entities.client_entity import Client
        from modules.cliente.domain.entities.address_entity import Address
        from decimal import Decimal
        from datetime import datetime, timezone
        
        # Converte os dados serializados de volta para entidades
        client = _deserialize_client(client_data)
        order = _deserialize_order(order_data, client)
        
        # Envia o email
        email_service = EmailService()
        result = email_service.send_refund_notification_email_to_customer(order, client, payment_info)
        
        if not result:
            # Se o email não foi enviado, tenta novamente
            raise ValueError("Email não foi enviado com sucesso")
        
        return result
        
    except Exception as e:
        # Registra o erro completo
        traceback.print_exc()
        
        # Tenta novamente se não atingiu o máximo de tentativas
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        else:
            return False


def _deserialize_client(client_data: Dict) -> Any:
    """Deserializa dados do cliente para entidade"""
    from modules.cliente.domain.entities.client_entity import Client
    from modules.cliente.domain.entities.address_entity import Address
    from datetime import datetime, timezone
    
    address_data = client_data.get('address', {})
    address = Address(
        address=address_data.get('address', ''),
        number=address_data.get('number', ''),
        complement=address_data.get('complement', ''),
        province=address_data.get('province', ''),
        city=address_data.get('city', ''),
        state=address_data.get('state', ''),
        postal_code=address_data.get('postal_code', '')
    )
    
    return Client(
        id=client_data.get('id'),
        name=client_data.get('name'),
        cpf=client_data.get('cpf'),
        phone=client_data.get('phone', ''),
        mobile_phone=client_data.get('mobile_phone', ''),
        address=address,
        email=client_data.get('email')
    )


def _deserialize_order(order_data: Dict, client: Any) -> Any:
    """Deserializa dados do pedido para entidade"""
    from modules.pedido.domain.entities.order_entity import Order, OrderItem
    from decimal import Decimal
    from datetime import datetime, timezone
    
    items_data = order_data.get('items', [])
    items = []
    for item_data in items_data:
        item = OrderItem(
            product_id=item_data.get('product_id'),
            product_name=item_data.get('product_name'),
            quantity=item_data.get('quantity'),
            unit_price=Decimal(str(item_data.get('unit_price', 0))),
            total_price=Decimal(str(item_data.get('total_price', 0)))
        )
        items.append(item)
    
    created_at = None
    if order_data.get('created_at'):
        created_at = datetime.fromisoformat(order_data['created_at'].replace('Z', '+00:00'))
    
    updated_at = None
    if order_data.get('updated_at'):
        updated_at = datetime.fromisoformat(order_data['updated_at'].replace('Z', '+00:00'))
    
    confirmed_at = None
    if order_data.get('confirmed_at'):
        confirmed_at = datetime.fromisoformat(order_data['confirmed_at'].replace('Z', '+00:00'))
    
    return Order(
        id=order_data.get('id'),
        client=client,
        items=items,
        subtotal=Decimal(str(order_data.get('subtotal', 0))),
        total=Decimal(str(order_data.get('total', 0))),
        status=order_data.get('status', 'PENDING'),
        external_reference=order_data.get('external_reference'),
        notes=order_data.get('notes'),
        created_at=created_at,
        updated_at=updated_at,
        confirmed_at=confirmed_at
    )

