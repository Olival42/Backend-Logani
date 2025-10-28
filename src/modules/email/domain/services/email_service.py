"""
Serviço de envio de emails para notificações de pedidos
"""

from django.core.mail import send_mail
from django.conf import settings
from datetime import timezone
import pytz
from modules.pedido.domain.entities.order_entity import Order
from modules.cliente.domain.entities.client_entity import Client


class EmailService:
    """
    Serviço para envio de emails relacionados a pedidos
    """
    
    def __init__(self):
        self.owner_email = settings.OWNER_EMAIL
    
    def send_order_confirmed_email(self, order: Order, client: Client) -> bool:
        """
        Envia email de notificação quando um pedido é confirmado
        
        Args:
            order: Entidade do pedido confirmado
            client: Entidade do cliente
            
        Returns:
            bool: True se o email foi enviado com sucesso
        """
        try:
            # Verifica se OWNER_EMAIL está configurado
            if not self.owner_email:
                return False
            
            subject = f"Novo Pedido Confirmado - {order.external_reference}"
            
            # Monta o corpo do email com informações completas
            message = self._build_order_confirmed_message(order, client)
            
            # Envia o email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.owner_email],
                fail_silently=False,
            )
            
            return True
            
        except Exception as e:
            return False
    
    def _build_order_confirmed_message(self, order: Order, client: Client) -> str:
        """
        Monta a mensagem do email formatada para frete/logística
        
        Args:
            order: Entidade do pedido
            client: Entidade do cliente
            
        Returns:
            str: Mensagem formatada para o email
        """
        # Informações dos produtos para embalagem
        items_info = []
        total_items_qty = 0
        for item in order.items:
            items_info.append(
                f"  - {item.quantity}x {item.product_name} (ID: {item.product_id})\n"
                f"    Total: R$ {item.total_price:.2f}"
            )
            total_items_qty += item.quantity
        
        items_text = "\n".join(items_info)
        
        # Informações de contato do cliente
        phone = client.phone or "Não informado"
        cellphone = client.mobile_phone or "Não informado"
        contact_info = f"📞 Telefone: {phone} / Celular: {cellphone}"
        
        # Informações de endereço para entrega
        address_info = ""
        if client.address:
            complement = f", {client.address.complement}" if client.address.complement else ""
            address_info = f"""ENDERECO DE ENTREGA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Destinatario: {client.name}
CPF: {client.cpf}
Contato: {contact_info}

Endereco Completo:
{client.address.address}, {client.address.number}{complement}
Bairro: {client.address.province}
Cidade: {client.address.city} - {client.address.state}
CEP: {client.address.postal_code}
"""
        else:
            address_info = "\nATENCAO: ENDERECO NAO INFORMADO\n"
        
        # Converte UTC para horário de Brasília
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        confirmed_at_brazil = order.confirmed_at.astimezone(brazil_tz)
        date_str = confirmed_at_brazil.strftime('%d/%m/%Y às %H:%M')
        
        # Monta a mensagem completa focada em logística
        message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              NOVO PEDIDO PARA ENVIO - FRETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PEDIDO: {order.external_reference}
Data/Hora: {date_str}
Valor Total: R$ {order.total:.2f}
Total de Itens: {total_items_qty} unidade(s)
Observacoes: {order.notes or 'Nenhuma'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRODUTOS PARA EMBALAR:

{items_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{address_info}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ IMPORTANTE ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Entre em contato com o cliente para confirmar o endereco e o valor do frete a pagar
✓ Separar produtos listados
✓ Embalar adequadamente para envio
✓ Preparar para entrega

═════════════════════════════════════════════════════════
Este email foi gerado automaticamente quando o pagamento foi confirmado.
Por favor, processe o pedido com urgência.
═════════════════════════════════════════════════════════
"""
        
        return message

