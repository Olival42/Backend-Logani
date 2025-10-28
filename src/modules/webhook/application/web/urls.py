from django.urls import path
from .views import (
    WebhookCreateView,
    WebhookListView,
    WebhookDetailView,
    WebhookUpdateView,
    WebhookDeleteView
)
from .views_webhook_receiver import AsaasWebhookReceiverView

urlpatterns = [
    # Endpoint público para receber notificações do ASAAS
    path('receive/', AsaasWebhookReceiverView.as_view(), name='webhook-receive'),
    
    # Criação de webhook
    path('create/', WebhookCreateView.as_view(), name='webhook-create'),
    
    # Listagem de webhooks
    path('list/', WebhookListView.as_view(), name='webhook-list'),
    
    # Detalhes de webhook
    path('detail/<str:webhook_id>/', WebhookDetailView.as_view(), name='webhook-detail'),
    
    # Atualização de webhook
    path('update/<str:webhook_id>/', WebhookUpdateView.as_view(), name='webhook-update'),
    
    # Remoção de webhook
    path('delete/<str:webhook_id>/', WebhookDeleteView.as_view(), name='webhook-delete'),
]

