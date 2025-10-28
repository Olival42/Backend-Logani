from django.db import models
from modules.cliente.adapters.persistence.models import Client
from modules.usuario.adapters.persistence.models import User


class OrderItem(models.Model):
    """
    Item de um pedido (produto)
    """
    id = models.UUIDField(primary_key=True, editable=False, default=None)
    product_id = models.CharField(max_length=100, help_text="ID do produto")
    product_name = models.CharField(max_length=255, help_text="Nome do produto")
    quantity = models.IntegerField(help_text="Quantidade")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Preço unitário")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Preço total")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "order_items"
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity} = R$ {self.total_price}"
    
    def save(self, *args, **kwargs):
        """Gera UUID automaticamente se não fornecido"""
        if not self.id:
            import uuid
            self.id = uuid.uuid4()
        super().save(*args, **kwargs)


class Order(models.Model):
    """
    Modelo para armazenar informações de pedidos
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('CONFIRMED', 'Confirmado'),
        ('PAID', 'Pago'),
        ('PREPARING', 'Em preparação'),
        ('CANCELLED', 'Cancelado'),
    ]
    
    id = models.UUIDField(primary_key=True, editable=False)
    
    # Cliente
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="orders",
        help_text="Cliente do pedido"
    )
    
    # Itens do pedido
    items = models.ManyToManyField(
        OrderItem,
        related_name="orders",
        help_text="Itens do pedido"
    )
    
    # Valores
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, help_text="Subtotal do pedido")
    total = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total do pedido")
    
    # Status
    status = models.CharField(
        max_length=50,
        default='PENDING',
        choices=STATUS_CHOICES,
        help_text="Status do pedido"
    )
    
    # Referência externa
    external_reference = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="Referência externa (ex: pedido_123)"
    )
    
    # Observações
    notes = models.TextField(blank=True, null=True, help_text="Observações do pedido")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(blank=True, null=True, help_text="Data de confirmação")
    
    class Meta:
        db_table = "orders"
        ordering = ['-created_at']
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
    
    def __str__(self):
        return f"Pedido #{self.external_reference or self.id} - {self.client.name} - R$ {self.total}"
    
    @property
    def is_pending(self):
        """Verifica se o pedido está pendente"""
        return self.status == 'PENDING'
    
    @property
    def is_confirmed(self):
        """Verifica se o pedido está confirmado"""
        return self.status == 'CONFIRMED'
    
    @property
    def is_cancelled(self):
        """Verifica se o pedido está cancelado"""
        return self.status == 'CANCELLED'
    
    @property
    def can_be_cancelled(self):
        """Verifica se o pedido pode ser cancelado"""
        return self.status in ['PENDING', 'CONFIRMED']
    
    @property
    def total_items(self):
        """Retorna a quantidade total de itens"""
        return sum(item.quantity for item in self.items.all())

