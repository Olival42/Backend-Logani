from rest_framework import serializers
from typing import List


class CreateWebhookSerializer(serializers.Serializer):
    """Serializer para criação de webhook"""
    
    url = serializers.URLField(
        required=True,
        help_text="URL do webhook"
    )
    
    events = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        min_length=1,
        help_text="Lista de eventos a serem notificados",
        error_messages={
            'required': 'O campo events é obrigatório.',
            'min_length': 'Pelo menos um evento deve ser informado.'
        }
    )
    
    email = serializers.EmailField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Email para notificações"
    )
    
    api_version = serializers.CharField(
        required=False,
        default='v3',
        max_length=10,
        help_text="Versão da API"
    )
    
    auth_token = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=255,
        help_text="Token de autenticação"
    )
    
    enabled = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Webhook habilitado"
    )
    
    def validate_url(self, value):
        """Valida a URL"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL deve começar com http:// ou https://")
        return value
    
    def validate_events(self, value):
        """Valida os eventos"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("Pelo menos um evento deve ser informado")
        
        # Eventos válidos do ASAAS (oficiais da documentação)
        valid_events = [
            # Eventos principais de pagamento (Core)
            'PAYMENT_CREATED',
            'PAYMENT_CONFIRMED',
            'PAYMENT_RECEIVED',
            'PAYMENT_OVERDUE',
            'PAYMENT_DELETED',
            'PAYMENT_REFUNDED',
            # Eventos de chargeback
            'PAYMENT_CHARGEBACK_REQUESTED',
            'PAYMENT_CHARGEBACK_DISPUTE',
            'PAYMENT_CHARGEBACK_REVERSAL',
        ]
        
        invalid_events = [event for event in value if event not in valid_events]
        if invalid_events:
            raise serializers.ValidationError(
                f"Eventos inválidos: {', '.join(invalid_events)}"
            )
        
        return value


class UpdateWebhookSerializer(serializers.Serializer):
    """Serializer para atualização de webhook"""
    
    url = serializers.URLField(
        required=False,
        help_text="URL do webhook"
    )
    
    events = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Lista de eventos"
    )
    
    email = serializers.EmailField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Email para notificações"
    )
    
    enabled = serializers.BooleanField(
        required=False,
        help_text="Webhook habilitado"
    )
    
    auth_token = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=255,
        help_text="Token de autenticação"
    )


class WebhookResponseSerializer(serializers.Serializer):
    """Serializer para resposta de webhook"""
    
    local_id = serializers.UUIDField()
    asaas_id = serializers.CharField()
    url = serializers.URLField()
    email = serializers.EmailField(allow_null=True)
    events = serializers.ListField(child=serializers.CharField())
    status = serializers.CharField()
    enabled = serializers.BooleanField()
    api_version = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class WebhookListSerializer(serializers.Serializer):
    """Serializer para listagem de webhooks"""
    
    id = serializers.UUIDField()
    url = serializers.URLField()
    email = serializers.EmailField(allow_null=True)
    events = serializers.ListField(child=serializers.CharField())
    status = serializers.CharField()
    enabled = serializers.BooleanField()
    created_at = serializers.DateTimeField()

