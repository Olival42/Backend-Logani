from django.db import models
from django.contrib.auth.models import User
from modules.cliente.adapters.persistence.models import Client


class Checkout(models.Model):
    """
    Modelo para armazenar informações de checkout do ASAAS
    """
    
    id = models.UUIDField(primary_key=True, editable=False)
    asaas_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    # Cliente associado
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="checkouts",
        help_text="Cliente associado ao checkout"
    )
    
    # Dados do checkout
    name = models.CharField(max_length=255, help_text="Nome do checkout")
    value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor do checkout")
    description = models.TextField(blank=True, null=True, help_text="Descrição do checkout")
    installments = models.IntegerField(default=1, help_text="Número de parcelas")
    status = models.CharField(
        max_length=50,
        default='PENDING',
        choices=[
            ('PENDING', 'Pendente'),
            ('CONFIRMED', 'Confirmado'),
            ('PAID', 'Pago'),
            ('RECEIVED', 'Recebido'),
            ('CANCELLED', 'Cancelado'),
            ('EXPIRED', 'Expirado'),
            ('REFUNDING', 'Estornando'),
            ('REFUNDED', 'Estornado'),
            ('FAILED', 'Falhou'),
        ],
        help_text="Status do checkout"
    )
    
    # URLs e configurações
    checkout_url = models.URLField(blank=True, null=True, help_text="URL do checkout")
    success_url = models.URLField(blank=True, null=True, help_text="URL de sucesso")
    failure_url = models.URLField(blank=True, null=True, help_text="URL de falha")
    expires_url = models.URLField(blank=True, null=True, help_text="URL de expiração")
    
    # Metadados
    external_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Referência externa"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(blank=True, null=True, help_text="Data de expiração")
    
    class Meta:
        db_table = "checkouts"
        ordering = ['-created_at']
        verbose_name = "Checkout"
        verbose_name_plural = "Checkouts"
    
    def __str__(self):
        return f"Checkout {self.name} - {self.client.name} - R$ {self.value}"
    
    @property
    def is_expired(self):
        """Verifica se o checkout expirou"""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False
    
    @property
    def is_paid(self):
        """Verifica se o checkout foi pago"""
        return self.status == 'PAID'
    
    @property
    def can_be_cancelled(self):
        """Verifica se o checkout pode ser cancelado"""
        return self.status in ['PENDING'] and not self.is_expired
