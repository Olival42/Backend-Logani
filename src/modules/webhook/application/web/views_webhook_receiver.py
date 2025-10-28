from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json

from modules.webhook.domain.services.webhook_notification_service import WebhookNotificationService
from modules.webhook.adapters.persistence.webhook_notification_repository_django import WebhookNotificationRepository
from modules.pagamento.adapters.persistence.payment_repository_django import PaymentRepository
from modules.pedido.adapters.persistence.order_repository_django import OrderRepository


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
            # Log da notificação recebida (para debug)
            print(f"Webhook recebido: {json.dumps(request.data, indent=2)}")
            
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
            return Response(
                {'message': 'Notificação recebida e processada com sucesso', 'result': result},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            # Em caso de erro, ainda retorna 200 para evitar reenvios
            # mas loga o erro para análise
            print(f"Erro ao processar webhook: {str(e)}")
            
            return Response(
                {'message': 'Erro ao processar notificação, mas foi registrado para análise'},
                status=status.HTTP_200_OK
            )

