from django.urls import path
from .views import (
    OrderCreateView,
    OrderDetailView,
    OrderConfirmView,
    OrderCancelView,
    OrderListByClientView,
    OrderUpdateView,
    OrderAddShippingView
)

urlpatterns = [
    # Criar pedido
    path('create/', OrderCreateView.as_view(), name='order-create'),
    
    # Detalhes de pedido
    path('detail/<str:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    
    # Atualizar pedido
    path('update/<str:order_id>/', OrderUpdateView.as_view(), name='order-update'),
    
    # Confirmar pedido
    path('confirm/<str:order_id>/', OrderConfirmView.as_view(), name='order-confirm'),
    
    # Cancelar pedido
    path('cancel/<str:order_id>/', OrderCancelView.as_view(), name='order-cancel'),
    
    # Listar pedidos do cliente
    path('my-orders/', OrderListByClientView.as_view(), name='order-list-client'),
    
    # Adicionar frete ao pedido
    path('add-shipping/<str:order_id>/', OrderAddShippingView.as_view(), name='order-add-shipping'),
]

