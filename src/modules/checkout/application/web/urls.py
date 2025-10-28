from django.urls import path
from .views import (
    CheckoutCreateView,
    CheckoutDetailView,
    CheckoutCancelView,
    CheckoutSyncView,
    CheckoutListView
)

urlpatterns = [
    # Criação de checkout
    path('create/', CheckoutCreateView.as_view(), name='checkout-create'),
    
    # Listagem de checkouts
    path('list/', CheckoutListView.as_view(), name='checkout-list'),
    
    # Detalhes de checkout
    path('detail/<str:checkout_id>/', CheckoutDetailView.as_view(), name='checkout-detail'),
    
    # Cancelamento de checkout
    path('cancel/<str:checkout_id>/', CheckoutCancelView.as_view(), name='checkout-cancel'),
    
    # Sincronização de checkout
    path('sync/<str:checkout_id>/', CheckoutSyncView.as_view(), name='checkout-sync'),
]
