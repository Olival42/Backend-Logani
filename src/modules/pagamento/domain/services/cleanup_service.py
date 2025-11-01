"""
Serviço para limpeza e reconciliação de recursos órfãos entre sistema local e Asaas
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.db import transaction

from modules.checkout.adapters.external.asaas_checkout_client import AsaasCheckoutClient
from modules.checkout.adapters.persistence.checkout_repository_django import CheckoutRepository
from modules.pagamento.adapters.persistence.payment_repository_django import PaymentRepository


class CleanupService:
    """
    Serviço para limpar recursos órfãos criados no Asaas que não foram salvos localmente
    """
    
    def __init__(self):
        self.asaas_client = AsaasCheckoutClient()
        self.checkout_repository = CheckoutRepository()
        self.payment_repository = PaymentRepository()
    
    def cleanup_orphaned_checkouts(self, asaas_checkout_ids: List[str]) -> Dict[str, Any]:
        """
        Limpa checkouts órfãos no Asaas (criados mas não salvos localmente)
        
        Args:
            asaas_checkout_ids: Lista de IDs de checkouts no Asaas para limpar
            
        Returns:
            Dict com resultados da limpeza
        """
        results = {
            'success': [],
            'failed': [],
            'not_found': []
        }
        
        for checkout_id in asaas_checkout_ids:
            try:
                # Tenta cancelar o checkout no Asaas
                self.asaas_client.cancel_checkout(checkout_id)
                results['success'].append(checkout_id)
                print(f"✅ Checkout órfão {checkout_id} cancelado com sucesso")
            except ValueError as e:
                error_msg = str(e)
                if 'não encontrado' in error_msg.lower() or 'not found' in error_msg.lower():
                    results['not_found'].append(checkout_id)
                    print(f"ℹ️ Checkout {checkout_id} não encontrado no Asaas (pode já ter sido cancelado)")
                else:
                    results['failed'].append({'checkout_id': checkout_id, 'error': error_msg})
                    print(f"❌ Erro ao cancelar checkout {checkout_id}: {error_msg}")
            except Exception as e:
                results['failed'].append({'checkout_id': checkout_id, 'error': str(e)})
                print(f"❌ Erro inesperado ao cancelar checkout {checkout_id}: {e}")
        
        return results
    
    def reconcile_checkout_status(self, asaas_checkout_id: str) -> Dict[str, Any]:
        """
        Reconcilia status de um checkout entre sistema local e Asaas
        
        Args:
            asaas_checkout_id: ID do checkout no Asaas
            
        Returns:
            Dict com informações da reconciliação
        """
        result = {
            'asaas_checkout_id': asaas_checkout_id,
            'exists_in_asaas': False,
            'exists_locally': False,
            'needs_cleanup': False,
            'action_taken': None
        }
        
        try:
            # Verifica se existe no Asaas
            asaas_checkout = self.asaas_client.get_checkout(asaas_checkout_id)
            result['exists_in_asaas'] = True
            result['asaas_status'] = asaas_checkout.get('status', 'UNKNOWN')
            
            # Verifica se existe localmente
            local_checkout = self.checkout_repository.get_by_asaas_id(asaas_checkout_id)
            if local_checkout:
                result['exists_locally'] = True
                result['local_status'] = local_checkout.status
                
                # Se existe nos dois lugares, compara status
                if result['asaas_status'] != result['local_status']:
                    result['status_mismatch'] = True
                    result['action_taken'] = 'sync_required'
            else:
                # Existe no Asaas mas não localmente - precisa limpar
                result['needs_cleanup'] = True
                
                # Só cancela se ainda estiver pendente
                if result['asaas_status'] in ['PENDING', 'ACTIVE']:
                    try:
                        self.asaas_client.cancel_checkout(asaas_checkout_id)
                        result['action_taken'] = 'cancelled_orphan'
                        print(f"✅ Checkout órfão {asaas_checkout_id} cancelado durante reconciliação")
                    except Exception as e:
                        result['action_taken'] = 'cleanup_failed'
                        result['cleanup_error'] = str(e)
                else:
                    result['action_taken'] = 'no_action_needed'
                    result['reason'] = f"Checkout já está no status {result['asaas_status']}"
                    
        except ValueError as e:
            # Checkout não existe no Asaas
            result['exists_in_asaas'] = False
            error_msg = str(e)
            if 'não encontrado' in error_msg.lower() or 'not found' in error_msg.lower():
                # Verifica se existe localmente mesmo assim (dados inconsistentes)
                local_checkout = self.checkout_repository.get_by_asaas_id(asaas_checkout_id)
                if local_checkout:
                    result['exists_locally'] = True
                    result['action_taken'] = 'data_inconsistency'
                    result['message'] = 'Checkout existe localmente mas não no Asaas - dados inconsistentes'
                else:
                    result['action_taken'] = 'already_cleaned'
                    result['message'] = 'Checkout não existe em nenhum lugar - já foi limpo ou nunca existiu'
        
        return result
    
    def cleanup_orphaned_payments(self, asaas_payment_ids: List[str]) -> Dict[str, Any]:
        """
        Limpa pagamentos órfãos no Asaas
        Nota: Normalmente não é possível "cancelar" pagamentos já processados,
        mas pode-se registrar para reconciliação
        
        Args:
            asaas_payment_ids: Lista de IDs de pagamentos no Asaas
            
        Returns:
            Dict com resultados
        """
        results = {
            'checked': [],
            'needs_attention': []
        }
        
        for payment_id in asaas_payment_ids:
            try:
                # Verifica se existe localmente
                local_payment = self.payment_repository.get_by_asaas_id(payment_id)
                
                if not local_payment:
                    results['needs_attention'].append({
                        'asaas_payment_id': payment_id,
                        'status': 'orphaned',
                        'action': 'manual_review_required'
                    })
                    print(f"⚠️ Pagamento órfão detectado: {payment_id}")
                else:
                    results['checked'].append({
                        'asaas_payment_id': payment_id,
                        'status': 'ok',
                        'local_id': str(local_payment.id)
                    })
            except Exception as e:
                results['needs_attention'].append({
                    'asaas_payment_id': payment_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results

