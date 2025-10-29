from rest_framework import serializers
from datetime import datetime, date
from decimal import Decimal


class CreateCheckoutSerializer(serializers.Serializer):
    """
    Serializer para criação de checkout baseado na documentação ASAAS
    Campos obrigatórios conforme: https://docs.asaas.com/reference/criar-novo-checkout
    """
    
    value = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        help_text="Valor do checkout",
        error_messages={
            "required": "O campo valor é obrigatório.",
            "invalid": "Valor inválido."
        }
    )
    
    customer = serializers.CharField(
        required=True,
        help_text="ID do cliente no ASAAS",
        error_messages={
            "required": "O campo customer é obrigatório.",
            "blank": "O campo customer é obrigatório."
        }
    )

    chargeTypes = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            ('DETACHED', 'Detached'),
            ('RECURRENT', 'Recurrent'),
            ('INSTALLMENT', 'Installment'),
        ]),
        required=True,
        help_text="Tipos de cobrança",
        error_messages={
            "required": "O campo chargeTypes é obrigatório.",
            "invalid": "Tipos de cobrança inválidos."
        }
    )
    
    minutesToExpire = serializers.IntegerField(
        required=True,
        help_text="Minutos para o vencimento",
        error_messages={
            "required": "O campo minutesToExpire é obrigatório.",
            "invalid": "Minutos para o vencimento inválido."
        }
    )
    
    # Campos opcionais conforme documentação ASAAS
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Descrição do checkout"
    )
    
    externalReference = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Referência externa para identificação"
    )
    
    # URLs de callback (opcionais)
    successUrl = serializers.URLField(
        required=True,
        allow_blank=True,
        allow_null=True,
        help_text="URL de redirecionamento em caso de sucesso",
        error_messages={
            "invalid": "URL de sucesso inválida.",
            "required": "O campo successUrl é obrigatório.",
        }
    )
    
    failureUrl = serializers.URLField(
        required=True,
        allow_blank=True,
        allow_null=True,
        help_text="URL de redirecionamento em caso de falha",
        error_messages={
            "invalid": "URL de falha inválida.",
            "required": "O campo failureUrl é obrigatório.",
        }
    )

    expiresUrl = serializers.URLField(
        required=True,
        allow_blank=True,
        allow_null=True,
        help_text="URL de redirecionamento em caso de expiração",
        error_messages={
            "invalid": "URL de expiração inválida.",
            "required": "O campo expiresUrl é obrigatório.",
        }
    )
    
    # Aceita callback como objeto aninhado
    callback = serializers.DictField(
        required=False,
        allow_null=True,
        help_text="Objeto com URLs de callback",
        error_messages={
            "invalid": "Callback deve ser um objeto."
        }
    )
    
    def to_internal_value(self, data):
        """Extrai URLs do objeto callback antes da validação"""
        # Se callback foi fornecido, move as URLs para o nível superior
        if 'callback' in data and isinstance(data['callback'], dict):
            callback_data = data['callback']
            
            # Move successUrl do callback para o nível superior
            if 'successUrl' in callback_data and 'successUrl' not in data:
                data['successUrl'] = callback_data['successUrl']
            
            # Move failureUrl do callback para o nível superior (ou cancelUrl, que o ASAAS usa)
            if 'failureUrl' in callback_data and 'failureUrl' not in data:
                data['failureUrl'] = callback_data['failureUrl']
            elif 'cancelUrl' in callback_data and 'failureUrl' not in data:
                # Mapeia cancelUrl para failureUrl (o ASAAS usa cancelUrl mas nossa entidade usa failureUrl)
                data['failureUrl'] = callback_data['cancelUrl']
            
            # Move expiredUrl do callback para o nível superior (Asaas usa expiredUrl)
            if 'expiredUrl' in callback_data and 'expiresUrl' not in data:
                data['expiresUrl'] = callback_data['expiredUrl']
            # Também aceita expiresUrl para compatibilidade
            elif 'expiresUrl' in callback_data and 'expiresUrl' not in data:
                data['expiresUrl'] = callback_data['expiresUrl']
            
            # Remove o objeto callback do data original
            data.pop('callback')
        
        return super().to_internal_value(data)
    
    # Configurações de pagamento (opcionais)
    installments = serializers.IntegerField(
        min_value=1,
        max_value=12,
        default=1,
        required=False,
        help_text="Número de parcelas",
        error_messages={
            "min_value": "Número mínimo de parcelas é 1.",
            "max_value": "Número máximo de parcelas é 12."
        }
    )
    
    paymentMethods = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            ('PIX', 'PIX'),
            ('CREDIT_CARD', 'Cartão de Crédito'),
            ('BOLETO', 'Boleto'),
        ]),
        required=False,
        allow_empty=True,
        help_text="Métodos de pagamento aceitos (se não informado, aceita todos)",
        error_messages={
            "invalid": "Lista de métodos de pagamento inválida."
        }
    )
    
    # Campo para itens do checkout
    items = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        allow_empty=True,
        help_text="Lista de itens do checkout",
        error_messages={
            "invalid": "Lista de itens inválida.",
            "required": "O campo items é obrigatório.",
        }
    )
    
    # Campo para configurações de parcelamento
    installment = serializers.DictField(
        required=False,
        allow_null=True,
        help_text="Configurações de parcelamento (maxInstallmentCount)",
        error_messages={
            "invalid": "Instalment deve ser um objeto."
        }
    )
    
    def validate_minutesToExpire(self, value):
        """Valida se os minutos para expiração são válidos"""
        if value <= 0:
            raise serializers.ValidationError("Minutos para expiração deve ser maior que zero.")
        if value > 10080:  # 7 dias em minutos
            raise serializers.ValidationError("Minutos para expiração não pode ser maior que 10080 (7 dias).")
        return value
    
    def validate_chargeTypes(self, value):
        """Valida se os tipos de cobrança são válidos"""
        if not value:
            raise serializers.ValidationError("Pelo menos um tipo de cobrança deve ser informado.")
        
        valid_types = ['DETACHED', 'RECURRENT', 'INSTALLMENT']
        for charge_type in value:
            if charge_type not in valid_types:
                raise serializers.ValidationError(f"Tipo de cobrança '{charge_type}' não é válido. Use: {', '.join(valid_types)}")
        
        return value
    
    def validate_value(self, value):
        """Valida se o valor é positivo"""
        if value <= 0:
            raise serializers.ValidationError("Valor deve ser maior que zero.")
        return value
    
    def validate_customer(self, value):
        """Valida se o customer ID está no formato correto"""
        if not value.startswith('cus_'):
            raise serializers.ValidationError("Customer ID deve começar com 'cus_'.")
        return value
    
    def validate_items(self, value):
        """Valida se os itens estão no formato correto"""
        if value:
            for item in value:
                if not isinstance(item, dict):
                    raise serializers.ValidationError("Cada item deve ser um objeto.")
                
                # Valida campos obrigatórios do item
                required_fields = ['name', 'value']
                for field in required_fields:
                    if field not in item:
                        raise serializers.ValidationError(f"Campo '{field}' é obrigatório em cada item.")
                
                # Valida se o valor é positivo
                try:
                    item_value = float(item['value'])
                    if item_value <= 0:
                        raise serializers.ValidationError("Valor do item deve ser maior que zero.")
                except (ValueError, TypeError):
                    raise serializers.ValidationError("Valor do item deve ser um número válido.")
                
                # Valida quantidade se informada
                if 'quantity' in item:
                    try:
                        quantity = int(item['quantity'])
                        if quantity <= 0:
                            raise serializers.ValidationError("Quantidade do item deve ser maior que zero.")
                    except (ValueError, TypeError):
                        raise serializers.ValidationError("Quantidade do item deve ser um número inteiro válido.")
        
        return value


class UpdateCheckoutSerializer(serializers.Serializer):
    """
    Serializer para atualização de checkout
    """
    
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Descrição do checkout"
    )
    
    successUrl = serializers.URLField(
        required=False,
        allow_blank=True,
        help_text="URL de redirecionamento em caso de sucesso"
    )
    
    failureUrl = serializers.URLField(
        required=False,
        allow_blank=True,
        help_text="URL de redirecionamento em caso de falha"
    )
    
    expiresUrl = serializers.URLField(
        required=False,
        allow_blank=True,
        help_text="URL de redirecionamento em caso de expiração"
    )
    
    externalReference = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Referência externa para identificação"
    )


class CheckoutResponseSerializer(serializers.Serializer):
    """
    Serializer para resposta de checkout
    """
    
    local_id = serializers.UUIDField()
    asaas_id = serializers.CharField()
    checkout_url = serializers.URLField()
    name = serializers.CharField()
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    expires_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class CheckoutListSerializer(serializers.Serializer):
    """
    Serializer para listagem de checkouts
    """
    
    id = serializers.UUIDField()
    name = serializers.CharField()
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    installments = serializers.IntegerField()
    checkout_url = serializers.URLField()
    created_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
    client_name = serializers.CharField(source='client.name')
    client_cpf = serializers.CharField(source='client.cpf')


class CheckoutDetailSerializer(serializers.Serializer):
    """
    Serializer para detalhes de checkout
    """
    
    id = serializers.UUIDField()
    asaas_id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    installments = serializers.IntegerField()
    checkout_url = serializers.URLField()
    successUrl = serializers.URLField()
    failureUrl = serializers.URLField()
    expiresUrl = serializers.URLField()
    externalReference = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
    client = serializers.DictField()
