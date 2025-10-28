from django.db import models


class Webhook(models.Model):
    """
    Modelo para armazenar configurações de Webhooks do ASAAS
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('ACTIVE', 'Ativo'),
        ('INACTIVE', 'Inativo'),
        ('ERROR', 'Erro'),
    ]
    
    id = models.UUIDField(primary_key=True, editable=False)
    asaas_webhook_id = models.CharField(
        max_length=50, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="ID do webhook no ASAAS"
    )
    
    # Configurações básicas
    url = models.URLField(
        max_length=500,
        help_text="URL do webhook",
        unique=True
    )
    
    email = models.EmailField(
        blank=True, 
        null=True,
        help_text="Email para notificações"
    )
    
    enabled = models.BooleanField(
        default=True,
        help_text="Webhook está habilitado"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        help_text="Status do webhook"
    )
    
    # Configurações de API
    api_version = models.CharField(
        max_length=10,
        default='v3',
        help_text="Versão da API"
    )
    
    auth_token = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Token de autenticação do webhook"
    )
    
    # Eventos cadastrados
    events = models.JSONField(
        default=list,
        help_text="Lista de eventos configurados"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "webhooks"
        ordering = ['-created_at']
        verbose_name = "Webhook"
        verbose_name_plural = "Webhooks"
    
    def __str__(self):
        return f"Webhook {self.url} - {len(self.events)} events - {self.status}"
    
    @property
    def is_active(self):
        """Verifica se o webhook está ativo"""
        return self.enabled and self.status == 'ACTIVE'


class WebhookNotification(models.Model):
    """
    Modelo para armazenar notificações de webhook recebidas do ASAAS
    """
    
    id = models.UUIDField(primary_key=True, editable=False, auto_created=True)
    
    # Identificadores do Asaas
    event = models.CharField(max_length=50, help_text="Tipo de evento")
    payment_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID do pagamento")
    subscription_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID da assinatura")
    installment_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID da parcela")
    customer_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID do cliente")
    
    # Datas
    payment_date = models.DateTimeField(blank=True, null=True, help_text="Data do pagamento")
    due_date = models.DateTimeField(blank=True, null=True, help_text="Data de vencimento")
    
    # Valores monetários
    value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Valor")
    net_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Valor líquido")
    original_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Valor original")
    interest_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Valor de juros")
    
    # Metadados
    description = models.TextField(blank=True, null=True, help_text="Descrição")
    external_reference = models.CharField(max_length=100, blank=True, null=True, help_text="Referência externa")
    billing_type = models.CharField(max_length=50, blank=True, null=True, help_text="Tipo de cobrança")
    status = models.CharField(max_length=50, blank=True, null=True, help_text="Status")
    
    # Dados completos da notificação
    data = models.JSONField(default=dict, help_text="Dados completos da notificação")
    
    # Controle de processamento
    processed = models.BooleanField(default=False, help_text="Notificação foi processada")
    processed_at = models.DateTimeField(blank=True, null=True, help_text="Data de processamento")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "webhook_notifications"
        ordering = ['-created_at']
        verbose_name = "Notificação de Webhook"
        verbose_name_plural = "Notificações de Webhook"
        indexes = [
            models.Index(fields=['event']),
            models.Index(fields=['payment_id']),
            models.Index(fields=['external_reference']),
            models.Index(fields=['processed']),
        ]
    
    def __str__(self):
        return f"Notification {self.event} - {self.external_reference}"
