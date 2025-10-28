from typing import Optional
from modules.webhook.domain.entities.webhook_notification_entity import WebhookNotification
from modules.webhook.adapters.persistence.models import WebhookNotification as WebhookNotificationModel
from decimal import Decimal


class WebhookNotificationRepository:
    """Repositório Django para notificações de webhook"""
    
    def save(self, notification: WebhookNotification) -> WebhookNotification:
        """Salva uma notificação de webhook"""
        model = WebhookNotificationModel.objects.create(
            id=notification.id,
            event=notification.event,
            payment_id=notification.payment_id,
            subscription_id=notification.subscription_id,
            installment_id=notification.installment_id,
            customer_id=notification.customer_id,
            payment_date=notification.payment_date,
            due_date=notification.due_date,
            value=notification.value,
            net_value=notification.net_value,
            original_value=notification.original_value,
            interest_value=notification.interest_value,
            description=notification.description,
            external_reference=notification.external_reference,
            billing_type=notification.billing_type,
            status=notification.status,
            data=notification.data,
            processed=notification.processed,
            processed_at=notification.processed_at
        )
        
        notification.id = str(model.id)
        return notification
    
    def get_by_id(self, notification_id: str) -> Optional[WebhookNotification]:
        """Busca uma notificação por ID"""
        try:
            model = WebhookNotificationModel.objects.get(id=notification_id)
            return self._model_to_entity(model)
        except WebhookNotificationModel.DoesNotExist:
            return None
    
    def get_by_payment_id(self, payment_id: str) -> Optional[WebhookNotification]:
        """Busca uma notificação por payment_id"""
        try:
            model = WebhookNotificationModel.objects.filter(
                payment_id=payment_id
            ).order_by('-created_at').first()
            if model:
                return self._model_to_entity(model)
            return None
        except WebhookNotificationModel.DoesNotExist:
            return None
    
    def get_by_external_reference(self, external_reference: str) -> list:
        """Busca notificações por external_reference"""
        models = WebhookNotificationModel.objects.filter(
            external_reference=external_reference
        ).order_by('-created_at')
        return [self._model_to_entity(model) for model in models]
    
    def list_unprocessed(self) -> list:
        """Lista notificações não processadas"""
        models = WebhookNotificationModel.objects.filter(
            processed=False
        ).order_by('created_at')
        return [self._model_to_entity(model) for model in models]
    
    def update(self, notification: WebhookNotification) -> WebhookNotification:
        """Atualiza uma notificação"""
        model = WebhookNotificationModel.objects.get(id=notification.id)
        
        model.event = notification.event
        model.payment_id = notification.payment_id
        model.status = notification.status
        model.data = notification.data
        model.processed = notification.processed
        model.processed_at = notification.processed_at
        
        model.save()
        return notification
    
    def _model_to_entity(self, model: WebhookNotificationModel) -> WebhookNotification:
        """Converte um modelo Django para entidade"""
        return WebhookNotification(
            id=str(model.id),
            event=model.event,
            payment_id=model.payment_id,
            subscription_id=model.subscription_id,
            installment_id=model.installment_id,
            customer_id=model.customer_id,
            payment_date=model.payment_date,
            due_date=model.due_date,
            value=model.value,
            net_value=model.net_value,
            original_value=model.original_value,
            interest_value=model.interest_value,
            description=model.description,
            external_reference=model.external_reference,
            billing_type=model.billing_type,
            status=model.status,
            data=model.data,
            created_at=model.created_at,
            processed=model.processed,
            processed_at=model.processed_at
        )

