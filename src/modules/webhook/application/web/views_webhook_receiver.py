from rest_framework.views import APIView

from modules.webhook.domain.services.webhook_notification_service import WebhookNotificationService
from modules.webhook.adapters.persistence.webhook_notification_repository_django import WebhookNotificationRepository
from modules.pagamento.adapters.persistence.payment_repository_django import PaymentRepository
from modules.pedido.adapters.persistence.order_repository_django import OrderRepository
from api_pagamento_frete.utils import SuccessResponse


class AsaasWebhookReceiverView(APIView):
    """
    View pública para receber notificações de webhook do ASAAS
    IMPORTANTE: Este endpoint não deve exigir autenticação pois é chamado pelo ASAAS
    """
    
    authentication_classes = []  # Sem autenticação
    permission_classes = []  # Sem permissões
    
    def post(self, request):
        """
        Endpoint para receber notificações do ASAAS
        
        Formato esperado:
        {
            "event": "PAYMENT_CONFIRMED",
            "payment": {
                "id": "pay_...",
                "customer": "cus_...",
                "value": 100.00,
                "status": "CONFIRMED",
                "billingType": "PIX",
                "externalReference": "pedido_123",
                ...
            }
        }
        """
        try:
            # Inicializa os serviços
            notification_repository = WebhookNotificationRepository()
            payment_repository = PaymentRepository()
            order_repository = OrderRepository()
            
            notification_service = WebhookNotificationService(
                notification_repository, 
                payment_repository,
                order_repository
            )
            
            # Salva a notificação recebida
            notification = notification_service.receive_and_save_notification(request.data)
            
            # Processa a notificação
            result = notification_service.process_notification(notification)
            
            # Retorna sucesso ao ASAAS (importante para evitar reenvios)
            return SuccessResponse.ok(
                data={'result': result},
                message='Notificação recebida e processada com sucesso'
            )
            
        except Exception as e:
            # Sempre retorna 200 OK para evitar reenvios do ASAAS
            return SuccessResponse.ok(
                data={'error': str(e)},
                message='Erro ao processar notificação, mas foi registrado para análise'
            )

