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
    
    # Ativo/Inativo
    active = models.BooleanField(
        default=True,
        help_text="Indica se o pedido está ativo. Pedidos sem itens são marcados como inativos."
    )
    
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


class OrderShipping(models.Model):
    """
    Modelo para armazenar informações do serviço de frete escolhido para um pedido
    """
    id = models.UUIDField(primary_key=True, editable=False)
    
    # Relacionamento com pedido (OneToOne - um pedido tem apenas um frete escolhido)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="shipping",
        help_text="Pedido relacionado"
    )
    
    # Informações do serviço de frete
    service_id = models.IntegerField(help_text="ID do serviço no Melhor Envio")
    service_name = models.CharField(max_length=255, help_text="Nome do serviço de frete")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Preço do frete")
    custom_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Preço customizado (se aplicável)"
    )
    delivery_time = models.IntegerField(help_text="Prazo de entrega em dias")
    custom_delivery_time = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Prazo customizado (se aplicável)"
    )
    currency = models.CharField(max_length=3, default='BRL', help_text="Moeda")
    
    # Informações da transportadora (armazenadas como JSON)
    company = models.JSONField(null=True, blank=True, help_text="Informações da transportadora")
    
    # CEPs
    from_postal_code = models.CharField(max_length=8, help_text="CEP de origem")
    to_postal_code = models.CharField(max_length=8, help_text="CEP de destino")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "order_shipping"
        verbose_name = "Frete do Pedido"
        verbose_name_plural = "Fretes dos Pedidos"
    
    def __str__(self):
        return f"Frete {self.service_name} - Pedido {self.order.external_reference or self.order.id}"
    
    @property
    def final_price(self):
        """Retorna o preço final considerando custom_price se disponível"""
        return self.custom_price if self.custom_price is not None else self.price
    
    @property
    def final_delivery_time(self):
        """Retorna o prazo final considerando custom_delivery_time se disponível"""
        return self.custom_delivery_time if self.custom_delivery_time is not None else self.delivery_time
    
    def save(self, *args, **kwargs):
        """Gera UUID automaticamente se não fornecido"""
        if not self.id:
            import uuid
            self.id = uuid.uuid4()
        super().save(*args, **kwargs)