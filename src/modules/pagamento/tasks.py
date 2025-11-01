"""
Tasks Celery para operações assíncronas de pagamento e limpeza
"""
from celery import shared_task
from typing import List
import traceback

from modules.pagamento.domain.services.cleanup_service import CleanupService


@shared_task(name='cleanup_orphaned_checkouts', bind=True, max_retries=3, default_retry_delay=300)
def cleanup_orphaned_checkouts_async(self, asaas_checkout_ids: List[str]) -> dict:
    """
    Task assíncrona para limpar checkouts órfãos no Asaas
    
    Args:
        self: Referência à task (usado para retry)
        asaas_checkout_ids: Lista de IDs de checkouts no Asaas para limpar
        
    Returns:
        Dict com resultados da limpeza
    """
    try:
        cleanup_service = CleanupService()
        result = cleanup_service.cleanup_orphaned_checkouts(asaas_checkout_ids)
        return result
    except Exception as e:
        print(f"Erro na task de limpeza de checkouts órfãos (tentativa {self.request.retries + 1}): {e}")
        traceback.print_exc()
        
        # Tenta novamente se não atingiu o máximo de tentativas
        if self.request.retries < self.max_retries:
            print(f"Tentando novamente em {self.default_retry_delay} segundos...")
            raise self.retry(exc=e)
        else:
            print(f"Máximo de tentativas atingido para limpeza de checkouts órfãos")
            return {'error': str(e), 'failed_checkouts': asaas_checkout_ids}


@shared_task(name='reconcile_checkout_status', bind=True, max_retries=3, default_retry_delay=300)
def reconcile_checkout_status_async(self, asaas_checkout_id: str) -> dict:
    """
    Task assíncrona para reconciliar status de um checkout
    
    Args:
        self: Referência à task (usado para retry)
        asaas_checkout_id: ID do checkout no Asaas
        
    Returns:
        Dict com informações da reconciliação
    """
    try:
        cleanup_service = CleanupService()
        result = cleanup_service.reconcile_checkout_status(asaas_checkout_id)
        return result
    except Exception as e:
        print(f"Erro na task de reconciliação de checkout (tentativa {self.request.retries + 1}): {e}")
        traceback.print_exc()
        
        # Tenta novamente se não atingiu o máximo de tentativas
        if self.request.retries < self.max_retries:
            print(f"Tentando novamente em {self.default_retry_delay} segundos...")
            raise self.retry(exc=e)
        else:
            print(f"Máximo de tentativas atingido para reconciliação de checkout {asaas_checkout_id}")
            return {'error': str(e), 'asaas_checkout_id': asaas_checkout_id}

