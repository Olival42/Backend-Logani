from django.db import models
from modules.cliente.adapters.persistence.models import Client
from modules.pedido.adapters.persistence.models import Order


class Payment(models.Model):
    """
    Modelo para armazenar informações de pagamento
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('PAID', 'Pago'),
        ('RECEIVED', 'Recebido'),
        ('CANCELLED', 'Cancelado'),
        ('EXPIRED', 'Expirado'),
        ('REFUNDING', 'Estornando'),
        ('REFUNDED', 'Estornado'),
        ('FAILED', 'Falhou'),
    ]
    
    # Métodos de pagamento
    PAYMENT_METHOD_CHOICES = [
        ('PIX', 'PIX'),
        ('CREDIT_CARD', 'Cartão de Crédito'),
        ('BOLETO', 'Boleto'),
    ]
    
    id = models.UUIDField(primary_key=True, editable=False)
    
    # Relacionamentos
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="payments",
        help_text="Cliente"
    )
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments",
        help_text="Pedido relacionado",
        null=True,
        blank=True
    )
    
    # ID no Asaas
    asaas_id = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="ID do pagamento no Asaas")
    asaas_checkout_id = models.CharField(max_length=50, blank=True, null=True, help_text="ID do checkout no Asaas")
    
    # Dados do pagamento
    value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor do pagamento")
    description = models.TextField(blank=True, null=True, help_text="Descrição do pagamento")
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, help_text="Método de pagamento")
    
    # Status
    status = models.CharField(
        max_length=50,
        default='PENDING',
        choices=STATUS_CHOICES,
        help_text="Status do pagamento"
    )
    
    # URLs
    checkout_url = models.URLField(blank=True, null=True, help_text="URL do checkout")
    payment_url = models.URLField(blank=True, null=True, help_text="URL de pagamento")
    
    # Referência externa
    external_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Referência externa"
    )
    
    # Parcelas
    installments = models.IntegerField(default=1, help_text="Número de parcelas")
    installment_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID da parcela no Asaas")
    installment_number = models.IntegerField(blank=True, null=True, help_text="Número da parcela (1, 2, 3...)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(blank=True, null=True, help_text="Data de expiração")
    paid_at = models.DateTimeField(blank=True, null=True, help_text="Data do pagamento")
    refunded_at = models.DateTimeField(blank=True, null=True, help_text="Data do estorno")
    
    class Meta:
        db_table = "payments"
        ordering = ['-created_at']
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"
    
    def __str__(self):
        return f"Pagamento R$ {self.value} - {self.get_status_display()}"
    
    @property
    def is_pending(self):
        """Verifica se o pagamento está pendente"""
        return self.status == 'PENDING'
    
    @property
    def is_paid(self):
        """Verifica se o pagamento foi pago"""
        return self.status in ['PAID', 'RECEIVED']
    
    @property
    def is_expired(self):
        """Verifica se o pagamento expirou"""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False
    
    @property
    def can_be_cancelled(self):
        """Verifica se o pagamento pode ser cancelado"""
        return self.status in ['PENDING'] and not self.is_expired
    
    @property
    def can_be_refunded(self):
        """Verifica se o pagamento pode ser estornado"""
        return self.status in ['PAID', 'RECEIVED']


class PaymentItem(models.Model):
    """
    Itens de um pagamento (opcional, para detalhamento)
    """
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="payment_items"
    )
    
    description = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_value = models.DecimalField(max_digits=10, decimal_places=2)
    total_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = "payment_items"

