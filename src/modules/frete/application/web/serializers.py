from rest_framework import serializers
from typing import List, Dict, Optional


class ProductInputSerializer(serializers.Serializer):
    """
    Serializer para entrada de produtos no cálculo de frete
    """
    product_id = serializers.CharField(required=True, help_text="ID do produto")
    quantity = serializers.IntegerField(required=True, min_value=1, help_text="Quantidade do produto")
    
    # Também aceita "id" como alternativa
    id = serializers.CharField(required=False, help_text="ID do produto (alternativa a product_id)")
    
    def validate(self, data):
        # Garante que pelo menos um dos campos está presente
        if not data.get('product_id') and not data.get('id'):
            raise serializers.ValidationError("product_id ou id deve ser informado")
        
        # Usa id se product_id não estiver presente
        if not data.get('product_id') and data.get('id'):
            data['product_id'] = data['id']
        
        return data


class ShippingCalculationSerializer(serializers.Serializer):
    """
    Serializer para cálculo de frete
    """
    from_postal_code = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="CEP de origem (formato: 00000000 ou 00000-000). Se não informado, usa OWNER_CEP do .env"
    )
    to_postal_code = serializers.CharField(
        required=True,
        help_text="CEP de destino (formato: 00000000 ou 00000-000)"
    )
    products = ProductInputSerializer(many=True, required=True, help_text="Lista de produtos")
    receipt = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Serviço adicional de Aviso de Recebimento (Correios e JadLog)"
    )
    own_hand = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Serviço adicional de Mãos Próprias (Correios)"
    )
    services = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="IDs dos serviços separados por vírgula (ex: '1,2,18')"
    )
    
    def validate_from_postal_code(self, value):
        # Se vazio, permite (será preenchido do .env)
        if not value:
            return value
        # Remove formatação
        value = ''.join(filter(str.isdigit, value))
        if len(value) != 8:
            raise serializers.ValidationError("CEP de origem deve ter 8 dígitos")
        return value
    
    def validate_to_postal_code(self, value):
        # Remove formatação
        value = ''.join(filter(str.isdigit, value))
        if len(value) != 8:
            raise serializers.ValidationError("CEP de destino deve ter 8 dígitos")
        return value


class ShippingQuoteSerializer(serializers.Serializer):
    """
    Serializer para resposta de cotação de frete
    """
    id = serializers.IntegerField()
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    custom_price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    currency = serializers.CharField(default='BRL')
    delivery_time = serializers.IntegerField()
    custom_delivery_time = serializers.IntegerField(allow_null=True)
    company = serializers.DictField(allow_null=True)
    
    # Campos calculados
    final_price = serializers.SerializerMethodField()
    final_delivery_time = serializers.SerializerMethodField()
    
    def get_final_price(self, obj):
        return obj.get_final_price()
    
    def get_final_delivery_time(self, obj):
        return obj.get_final_delivery_time()


class AuthTokenSerializer(serializers.Serializer):
    """
    Serializer para autenticação com código de autorização
    """
    authorization_code = serializers.CharField(
        required=True,
        help_text="Código de autorização obtido após redirecionamento OAuth"
    )
    redirect_uri = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="URI de redirecionamento (opcional, usa o padrão se não informado)"
    )


class RefreshTokenSerializer(serializers.Serializer):
    """
    Serializer para resposta de token
    """
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    expires_in = serializers.IntegerField()
    token_type = serializers.CharField(default='Bearer')

