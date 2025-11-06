"""
Serviço de envio de emails para notificações de pedidos
"""

from typing import List, Dict
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timezone
import pytz
import os
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
        email = client.email or "Não informado"
        
        # Informações de endereço para entrega
        address_info = ""
        if client.address:
            complement = f", {client.address.complement}" if client.address.complement else ""
            address_info = f"""ENDERECO DE ENTREGA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Destinatario: {client.name}
CPF: {client.cpf}
Contato: {contact_info}
Email: {email}

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
    
    def send_order_cancelled_email(self, order: Order, client: Client, refund_info: List[Dict] = None) -> bool:
        """
        Envia email de notificação quando um pedido é cancelado
        
        Args:
            order: Entidade do pedido cancelado
            client: Entidade do cliente
            refund_info: Lista com informações de estorno (opcional)
            
        Returns:
            bool: True se o email foi enviado com sucesso
        """
        try:
            # Verifica se OWNER_EMAIL está configurado
            if not self.owner_email:
                return False
            
            subject = f"Pedido Cancelado - {order.external_reference}"
            
            # Monta o corpo do email com informações completas
            message = self._build_order_cancelled_message(order, client, refund_info)
            
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
            print(f"Erro ao enviar email de cancelamento: {e}")
            return False
    
    def _build_order_cancelled_message(self, order: Order, client: Client, refund_info: List[Dict] = None) -> str:
        """
        Monta a mensagem do email de cancelamento formatada
        
        Args:
            order: Entidade do pedido
            client: Entidade do cliente
            refund_info: Lista com informações de estorno
            
        Returns:
            str: Mensagem formatada para o email
        """
        # Informações dos produtos
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
        email = client.email or "Não informado"
        
        # Informações de endereço
        address_info = ""
        if client.address:
            complement = f", {client.address.complement}" if client.address.complement else ""
            address_info = f"""
Endereco do Cliente:
{client.address.address}, {client.address.number}{complement}
Bairro: {client.address.province}
Cidade: {client.address.city} - {client.address.state}
CEP: {client.address.postal_code}
"""
        # Converte UTC para horário de Brasília
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        cancelled_at = order.updated_at.astimezone(brazil_tz) if order.updated_at else datetime.now(timezone.utc).astimezone(brazil_tz)
        date_str = cancelled_at.strftime('%d/%m/%Y às %H:%M')
        
        created_at_str = ""
        if order.created_at:
            created_at_brazil = order.created_at.astimezone(brazil_tz)
            created_at_str = created_at_brazil.strftime('%d/%m/%Y às %H:%M')
        
        # Monta a mensagem completa
        message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              PEDIDO CANCELADO - NOTIFICACAO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PEDIDO: {order.external_reference}
Data de Criacao: {created_at_str if created_at_str else 'Não disponível'}
Data/Hora do Cancelamento: {date_str}
Valor Total: R$ {order.total:.2f}
Total de Itens: {total_items_qty} unidade(s)
Observacoes: {order.notes or 'Nenhuma'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFORMACOES DO CLIENTE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Nome: {client.name}
CPF: {client.cpf}
Email: {email}
Telefone: {phone}
Celular: {cellphone}

{address_info}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRODUTOS DO PEDIDO CANCELADO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{items_text}

⚠️ ACAO NECESSARIA ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Verificar se os estornos foram processados corretamente
✓ Confirmar se o cliente foi notificado sobre o cancelamento
✓ Repor produtos no estoque (se aplicável)
✓ Cancelar envios agendados (se houver)

════════════════════════════════════════════════════════════════
Este email foi gerado automaticamente quando o pedido foi cancelado.
Por favor, tome as providências necessárias.
════════════════════════════════════════════════════════════════
"""
        
        return message
    
    def send_order_cancelled_email_to_customer(self, order: Order, client: Client) -> bool:
        """
        Envia email ao cliente quando seu pedido for cancelado
        
        Args:
            order: Entidade do pedido cancelado
            client: Entidade do cliente
            
        Returns:
            bool: True se o email foi enviado com sucesso
        """
        try:
            # Verifica se o cliente tem email
            if not client.email:
                print("Cliente não possui email cadastrado")
                return False
            
            subject = f"Pedido Cancelado - {order.external_reference}"
            
            # Monta o corpo do email
            message = self._build_order_cancelled_customer_message(order, client)
            
            # Envia o email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[client.email],
                fail_silently=False,
            )
            
            return True
            
        except Exception as e:
            print(f"Erro ao enviar email de cancelamento para o cliente: {e}")
            return False
    
    def _build_order_cancelled_customer_message(self, order: Order, client: Client) -> str:
        """
        Monta a mensagem do email de cancelamento para o cliente
        
        Args:
            order: Entidade do pedido
            client: Entidade do cliente
            
        Returns:
            str: Mensagem formatada para o email
        """
        # Informações dos produtos
        items_info = []
        total_items_qty = 0
        for item in order.items:
            items_info.append(
                f"  - {item.quantity}x {item.product_name}\n"
                f"    Total: R$ {item.total_price:.2f}"
            )
            total_items_qty += item.quantity
        
        items_text = "\n".join(items_info)
        
        # Converte UTC para horário de Brasília
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        cancelled_at = order.updated_at.astimezone(brazil_tz) if order.updated_at else datetime.now(timezone.utc).astimezone(brazil_tz)
        date_str = cancelled_at.strftime('%d/%m/%Y às %H:%M')
        
        created_at_str = ""
        if order.created_at:
            created_at_brazil = order.created_at.astimezone(brazil_tz)
            created_at_str = created_at_brazil.strftime('%d/%m/%Y às %H:%M')
        
        # Monta a mensagem completa
        message = f"""
Olá {client.name},

Informamos que o pedido {order.external_reference} foi cancelado.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DETALHES DO PEDIDO CANCELADO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pedido: {order.external_reference}
Data de Criação: {created_at_str if created_at_str else 'Não disponível'}
Data do Cancelamento: {date_str}
Valor: R$ {order.total:.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRODUTOS DO PEDIDO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{items_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OBSERVAÇÕES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{order.notes or 'Nenhuma'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFORMAÇÕES IMPORTANTES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Se o pagamento já foi confirmado, o estorno será processado automaticamente
✓ O valor será creditado na mesma forma de pagamento utilizada na compra
✓ O prazo para o crédito pode levar de 1 a 3 dias úteis, dependendo da instituição financeira
✓ Você receberá um email separado quando o estorno for processado

Caso tenha alguma dúvida sobre o cancelamento ou estorno, entre em contato conosco.

Agradecemos sua compreensão.

Atenciosamente,
Equipe de Atendimento
"""
        
        return message
    
    def send_refund_notification_email_to_customer(self, order: Order, client: Client, payment_info: Dict = None) -> bool:
        """
        Envia email ao cliente quando o estorno for processado
        
        Args:
            order: Entidade do pedido
            client: Entidade do cliente
            payment_info: Informações sobre o pagamento estornado
            
        Returns:
            bool: True se o email foi enviado com sucesso
        """
        try:
            # Verifica se o cliente tem email
            if not client.email:
                print("Cliente não possui email cadastrado")
                return False
            
            subject = f"Estorno Processado - Pedido {order.external_reference}"
            
            # Monta o corpo do email
            message = self._build_refund_customer_message(order, client, payment_info)
            
            # Envia o email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[client.email],
                fail_silently=False,
            )
            
            return True
            
        except Exception as e:
            print(f"Erro ao enviar email de estorno para o cliente: {e}")
            return False
    
    def _build_refund_customer_message(self, order: Order, client: Client, payment_info: Dict = None) -> str:
        """
        Monta a mensagem do email de estorno para o cliente
        
        Args:
            order: Entidade do pedido
            client: Entidade do cliente
            payment_info: Informações sobre o pagamento
            
        Returns:
            str: Mensagem formatada para o email
        """
        # Informações dos produtos
        items_info = []
        total_items_qty = 0
        for item in order.items:
            items_info.append(
                f"  - {item.quantity}x {item.product_name}\n"
                f"    Total: R$ {item.total_price:.2f}"
            )
            total_items_qty += item.quantity
        
        items_text = "\n".join(items_info)
        
        # Converte UTC para horário de Brasília
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        updated_at = order.updated_at.astimezone(brazil_tz) if order.updated_at else datetime.now(timezone.utc).astimezone(brazil_tz)
        date_str = updated_at.strftime('%d/%m/%Y às %H:%M')
        
        created_at_str = ""
        if order.created_at:
            created_at_brazil = order.created_at.astimezone(brazil_tz)
            created_at_str = created_at_brazil.strftime('%d/%m/%Y às %H:%M')
        
        # Informações sobre o estorno
        refund_info = ""
        if payment_info:
            refund_info = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFORMAÇÕES DO ESTORNO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Método de Pagamento: {payment_info.get('payment_method', 'Não informado')}
Status do Estorno: Processado com sucesso
"""
        
        # Monta a mensagem completa
        message = f"""
Olá {client.name},

Informamos que o estorno do seu pagamento referente ao pedido {order.external_reference} foi processado com sucesso.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DETALHES DO ESTORNO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pedido: {order.external_reference}
Data de Criação: {created_at_str if created_at_str else 'Não disponível'}
Data do Estorno: {date_str}
Valor Estornado: R$ {order.total:.2f}

{refund_info}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRODUTOS DO PEDIDO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{items_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFORMAÇÕES IMPORTANTES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ O valor será creditado na mesma forma de pagamento utilizada na compra original
✓ O prazo para o crédito pode levar de 1 a 3 dias úteis, dependendo da instituição financeira
✓ Você pode verificar o crédito na sua conta bancária ou cartão de crédito
✓ Caso tenha alguma dúvida sobre o estorno, entre em contato conosco

Observações: {order.notes or 'Nenhuma'}

Agradecemos sua compreensão.

Atenciosamente,
Equipe de Atendimento
"""
        
        return message
    
    def send_password_reset_email(self, user_email: str, user_name: str, reset_token: str, reset_url: str = None) -> bool:
        """
        Envia email com link para reset de senha
        
        Args:
            user_email: Email do usuário
            user_name: Nome do usuário
            reset_token: Token de reset de senha
            reset_url: URL completa para reset (opcional, será construída se não fornecida)
            
        Returns:
            bool: True se o email foi enviado com sucesso
        """
        try:
            # Se não foi fornecida uma URL, constrói uma padrão
            if not reset_url:
                # Pega a URL base do frontend ou usa uma padrão
                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
                reset_url = f"{frontend_url}/reset-password?token={reset_token}"
            
            subject = "Redefinição de Senha"
            
            # Monta o corpo do email
            message = self._build_password_reset_message(user_name, reset_url, reset_token)
            
            # Envia o email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=False,
            )
            
            return True
            
        except Exception as e:
            print(f"Erro ao enviar email de reset de senha: {e}")
            return False
    
    def _build_password_reset_message(self, user_name: str, reset_url: str, reset_token: str) -> str:
        """
        Monta a mensagem do email de reset de senha
        
        Args:
            user_name: Nome do usuário
            reset_url: URL completa para reset
            reset_token: Token de reset (para caso o usuário precise copiar manualmente)
            
        Returns:
            str: Mensagem formatada para o email
        """
        message = f"""
Olá {user_name},

Você solicitou a redefinição de senha da sua conta.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REDEFINIR SENHA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Clique no link abaixo para redefinir sua senha:

{reset_url}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Este link expira em 1 hora
✓ O link pode ser usado apenas uma vez
✓ Se você não solicitou esta redefinição, ignore este email
✓ Sua senha não será alterada até que você clique no link e defina uma nova senha

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SE O LINK NÃO FUNCIONAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Se o link acima não funcionar, você pode copiar e colar o token abaixo na página de reset de senha:

Token: {reset_token}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Se você não solicitou esta redefinição, pode ignorar este email com segurança.

Atenciosamente,
Equipe de Suporte
"""
        return message