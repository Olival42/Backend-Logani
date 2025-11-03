from rest_framework import serializers
from decimal import Decimal


class OrderItemRequestSerializer(serializers.Serializer):
    """Serializer para receber item do pedido (ID e quantidade)"""
    
    product_id = serializers.CharField(
        required=True,
        help_text="ID do produto",
        error_messages={
            "required": "O campo product_id é obrigatório."
        }
    )
    
    quantity = serializers.IntegerField(
        required=True,
        min_value=1,
        help_text="Quantidade",
        error_messages={
            "required": "O campo quantity é obrigatório.",
            "min_value": "A quantidade deve ser maior que zero."
        }
    )


class OrderItemResponseSerializer(serializers.Serializer):
    """Serializer para responder item do pedido (com todos os dados)"""
    
    product_id = serializers.CharField(help_text="ID do produto")
    product_name = serializers.CharField(help_text="Nome do produto")
    quantity = serializers.IntegerField(help_text="Quantidade")
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Preço unitário")
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Preço total")


class CreateOrderSerializer(serializers.Serializer):
    """Serializer para criação de pedido"""
    
    items = OrderItemRequestSerializer(many=True, required=True)
    
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Observações do pedido"
    )
    
    def validate_items(self, value):
        """Valida se há pelo menos um item"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("O pedido deve ter pelo menos um item.")
        return value


class ClientSimpleSerializer(serializers.Serializer):
    """Serializer simplificado para cliente no pedido"""
    
    id = serializers.UUIDField()
    name = serializers.CharField()


class PaymentSimpleSerializer(serializers.Serializer):
    """Serializer simplificado para pagamento no pedido"""
    
    id = serializers.UUIDField()
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.CharField()
    status = serializers.CharField()
    installments = serializers.IntegerField()
    checkout_url = serializers.URLField(allow_null=True)
    created_at = serializers.DateTimeField()
    paid_at = serializers.DateTimeField(allow_null=True)


class OrderResponseSerializer(serializers.Serializer):
    """Serializer para resposta de pedido"""
    
    order_id = serializers.UUIDField()
    external_reference = serializers.CharField()
    client = ClientSimpleSerializer()
    items = OrderItemResponseSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_items = serializers.IntegerField()
    status = serializers.CharField()
    notes = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    confirmed_at = serializers.DateTimeField(allow_null=True)


class OrderDetailSerializer(serializers.Serializer):
    """Serializer para detalhes completos do pedido"""
    
    order_id = serializers.UUIDField()
    external_reference = serializers.CharField()
    
    client = ClientSimpleSerializer()
    
    items = OrderItemResponseSerializer(many=True)
    
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    status = serializers.CharField()
    notes = serializers.CharField(allow_null=True)
    
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    confirmed_at = serializers.DateTimeField(allow_null=True)


class UpdateOrderStatusSerializer(serializers.Serializer):
    """Serializer para atualização de status do pedido"""
    
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Observações sobre a mudança de status"
    )

