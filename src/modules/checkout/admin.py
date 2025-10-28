from django.contrib import admin
from .adapters.persistence.models import Checkout


@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    """
    Admin para o modelo Checkout
    """
    
    list_display = [
        'id',
        'name',
        'client',
        'value',
        'status',
        'installments',
        'expires_at',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'installments',
        'created_at',
        'expires_at'
    ]
    
    search_fields = [
        'name',
        'client__name',
        'client__cpf',
        'asaas_id',
        'external_reference'
    ]
    
    readonly_fields = [
        'id',
        'asaas_id',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('id', 'asaas_id', 'name', 'value', 'description', 'status')
        }),
        ('Cliente', {
            'fields': ('client',)
        }),
        ('Configurações', {
            'fields': ('installments', 'external_reference')
        }),
        ('URLs', {
            'fields': ('checkout_url', 'success_url', 'failure_url', 'expires_url')
        }),
        ('Datas', {
            'fields': ('expires_at', 'created_at', 'updated_at')
        }),
    )
    
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        """Otimiza as consultas"""
        return super().get_queryset(request).select_related('client')
