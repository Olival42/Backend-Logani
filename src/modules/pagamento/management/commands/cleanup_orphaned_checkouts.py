"""
Comando Django para limpar checkouts órfãos manualmente
Uso: python manage.py cleanup_orphaned_checkouts --checkout-id <id> [--reconcile]
"""
from django.core.management.base import BaseCommand
from modules.pagamento.domain.services.cleanup_service import CleanupService


class Command(BaseCommand):
    help = 'Limpa checkouts órfãos criados no Asaas que não foram salvos localmente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--checkout-ids',
            nargs='+',
            type=str,
            help='IDs dos checkouts no Asaas para limpar'
        )
        parser.add_argument(
            '--reconcile',
            type=str,
            help='ID de checkout para reconciliar status entre sistema local e Asaas'
        )
        parser.add_argument(
            '--auto-reconcile',
            action='store_true',
            help='Tenta encontrar e reconciliar checkouts órfãos automaticamente'
        )

    def handle(self, *args, **options):
        cleanup_service = CleanupService()
        
        if options['checkout_ids']:
            self.stdout.write(f"Lim encountered {len(options['checkout_ids'])} checkouts para limpar...")
            result = cleanup_service.cleanup_orphaned_checkouts(options['checkout_ids'])
            
            self.stdout.write(self.style.SUCCESS(f"\n✅ Sucesso: {len(result['success'])}"))
            self.stdout.write(self.style.WARNING(f"⚠️ Não encontrados: {len(result['not_found'])}"))
            self.stdout.write(self.style.ERROR(f"❌ Falhas: {len(result['failed'])}"))
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f"\nCheckouts cancelados: {', '.join(result['success'])}"))
            
            if result['failed']:
                self.stdout.write(self.style.ERROR(f"\nFalhas ao cancelar:"))
                for failure in result['failed']:
                    self.stdout.write(self.style.ERROR(f"  - {failure['checkout_id']}: {failure['error']}"))
        
        elif options['reconcile']:
            self.stdout.write(f"Reconciliando checkout {options['reconcile']}...")
            result = cleanup_service.reconcile_checkout_status(options['reconcile'])
            
            self.stdout.write(f"\nExiste no Asaas: {result['exists_in_asaas']}")
            self.stdout.write(f"Existe localmente: {result['exists_locally']}")
            
            if result.get('action_taken'):
                self.stdout.write(self.style.SUCCESS(f"Ação tomada: {result['action_taken']}"))
            
            if result.get('needs_cleanup'):
                self.stdout.write(self.style.WARNING("⚠️ Checkout precisa de limpeza"))
        
        elif options['auto_reconcile']:
            self.stdout.write(self.style.WARNING("Auto-reconciliação não implementada ainda"))
            self.stdout.write("Use --reconcile <id> para reconciliar um checkout específico")
        
        else:
            self.stdout.write(self.style.ERROR('Use --checkout-ids <id1> <id2> ... ou --reconcile <id>'))

