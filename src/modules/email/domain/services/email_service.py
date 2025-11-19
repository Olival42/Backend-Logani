"""
Serviço de envio de emails para notificações de pedidos
"""

from typing import List, Dict, Optional, Tuple
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from datetime import datetime, timezone
import pytz
import os
from dataclasses import dataclass
from pathlib import Path
from string import Template
from html import escape
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from modules.pedido.domain.entities.order_entity import Order
from modules.cliente.domain.entities.client_entity import Client


class EmailService:
    """
    Serviço para envio de emails relacionados a pedidos
    """
    
    def __init__(self):
        self.owner_email = settings.OWNER_EMAIL
        self.templates_dir = (
            Path(__file__).resolve().parent.parent / "templates"
        )
        # Garante que a pasta exista para facilitar deploys limpos
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir = self.templates_dir / "img"
    
    def send_contact_message(
        self,
        contact_name: str,
        contact_email: str,
        message: str,
        client: Optional[Client] = None,
    ) -> bool:
        """
        Envia uma mensagem de contato recebida via formulário.

        Args:
            contact_name: Nome informado no formulário.
            contact_email: Email informado no formulário.
            message: Mensagem escrita pelo usuário.
            client: Cliente associado ao usuário autenticado (opcional).

        Returns:
            bool: True se o email foi enviado com sucesso.
        """
        try:
            if not self.owner_email:
                return False

            subject = f"Nova mensagem de contato - {contact_name}"
            text_body, html_body, inline_assets = self._build_contact_message_payload(
                contact_name=contact_name,
                contact_email=contact_email,
                message=message,
                client=client,
            )
            self._send_email_with_html(
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                recipients=[self.owner_email],
                inline_assets=inline_assets,
            )
            return True
        except Exception:
            return False
    
    def _build_shipping_details(self, order: Order) -> str:
        """
        Monta uma descrição textual com os dados do frete associado ao pedido.
        """
        shipping = getattr(order, 'shipping', None)

        if not shipping:
            return (
                "Nenhum frete selecionado até o momento.\n"
                "✓ Realizar a cotação no Melhor Envio ou atualizar o pedido quando houver definição."
            )

        company_info = shipping.company or {}
        company_name = (
            company_info.get('name')
            or company_info.get('fantasy_name')
            or company_info.get('legal_name')
            or company_info.get('razao_social')
            or "Não informado"
        )
        company_document = (
            company_info.get('document')
            or company_info.get('cnpj')
            or company_info.get('cpf')
        )

        lines = [
            f"Serviço: {shipping.service_name} (ID: {shipping.service_id})",
            f"Transportadora: {company_name}",
        ]

        if company_document:
            lines.append(f"Documento: {company_document}")

        lines.append(f"Valor final aplicado: R$ {shipping.final_price:.2f} {shipping.currency}")
        if shipping.custom_price is not None and shipping.custom_price != shipping.price:
            lines.append(f"⚠️ Valor base da cotação: R$ {shipping.price:.2f} {shipping.currency}")
            lines.append(f"⚠️ Valor customizado informado: R$ {shipping.custom_price:.2f} {shipping.currency}")
        else:
            lines.append(f"Valor base da cotação: R$ {shipping.price:.2f} {shipping.currency}")

        lines.append(f"Prazo estimado: {shipping.final_delivery_time} dia(s)")
        if shipping.custom_delivery_time is not None and shipping.custom_delivery_time != shipping.delivery_time:
            lines.append(f"⚠️ Prazo base informado pelo Melhor Envio: {shipping.delivery_time} dia(s)")

        lines.append(f"CEP de origem: {shipping.from_postal_code or 'Não informado'}")
        lines.append(f"CEP de destino: {shipping.to_postal_code or 'Não informado'}")

        tracking_site = company_info.get('website') or company_info.get('url')
        if tracking_site:
            lines.append(f"Site para rastreio/contratação: {tracking_site}")

        return "\n".join(lines)

    def _render_email_template(self, template_name: str, context: Dict[str, str]) -> str:
        """
        Carrega e renderiza um template HTML simples usando string.Template.
        """
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template não encontrado: {template_path}")

        template_content = template_path.read_text(encoding="utf-8")
        template = Template(template_content)
        return template.safe_substitute(**context)

    @dataclass
    class InlineAsset:
        cid: str
        filename: str
        content: bytes
        mime_type: str

    def _load_binary_asset(self, asset_name: str) -> Optional[bytes]:
        """
        Retorna o conteúdo binário de um ativo, se existir.
        """
        asset_path = self.assets_dir / asset_name
        if not asset_path.exists():
            return None
        return asset_path.read_bytes()

    def _build_branding(self) -> Tuple[str, List["EmailService.InlineAsset"]]:
        """
        Retorna o bloco HTML da marca e os ativos inline necessários.
        """
        inline_assets: List[EmailService.InlineAsset] = []
        brand_element = '<p class="brand">LOGANI</p>'
        logo_bytes = self._load_binary_asset("logo.png")
        if logo_bytes:
            brand_element = (
                '<img src="cid:logo_inline" alt="Logani" class="brand-logo" />'
            )
            inline_assets.append(
                EmailService.InlineAsset(
                    cid="logo_inline",
                    filename="logo.png",
                    content=logo_bytes,
                    mime_type="image/png",
                )
            )
        return brand_element, inline_assets

    def _send_email_with_html(
        self,
        subject: str,
        text_body: str,
        html_body: str,
        recipients: List[str],
        inline_assets: Optional[List["EmailService.InlineAsset"]] = None,
    ) -> None:
        """
        Envia um email com versões em texto e HTML, anexando imagens inline se necessário.
        """
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        email.attach_alternative(html_body, "text/html")

        if inline_assets:
            email.mixed_subtype = "related"
            for asset in inline_assets:
                maintype, subtype = asset.mime_type.split("/", 1)
                if maintype == "image":
                    part = MIMEImage(asset.content, _subtype=subtype)
                else:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(asset.content)
                    encoders.encode_base64(part)

                part.add_header("Content-ID", f"<{asset.cid}>")
                part.add_header(
                    "Content-Disposition", "inline", filename=asset.filename
                )
                email.attach(part)

        email.send(fail_silently=False)

    def _build_contact_message_payload(
        self,
        contact_name: str,
        contact_email: str,
        message: str,
        client: Optional[Client] = None,
    ) -> Tuple[str, str, List["EmailService.InlineAsset"]]:
        """
        Monta as versões em texto e HTML para o email de contato.

        Args:
            contact_name: Nome informado no formulário.
            contact_email: Email informado no formulário.
            message: Mensagem escrita pelo usuário.
            client: Cliente associado ao usuário autenticado (opcional).

        Returns:
            Tuple[str, str, List[InlineAsset]]: Texto, HTML e ativos inline.
        """
        contact_name_value = (contact_name or "").strip() or "Não informado"
        contact_email_value = (contact_email or "").strip() or "Não informado"
        message_text = message.strip() or "Mensagem não informada."
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "                    NOVA MENSAGEM DE CONTATO",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "DETALHES DO FORMULÁRIO:",
            f"- Nome informado: {contact_name_value}",
            f"- Email informado: {contact_email_value}",
            "",
            "Mensagem:",
            f"{message_text}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "DADOS DO CLIENTE AUTENTICADO:",
        ]

        client_rows = []
        address_rows = []

        if client:
            user_email = getattr(client, "email", None)
            if not user_email and getattr(client, "user", None):
                user_email = getattr(client.user, "email", None)

            lines.extend(
                [
                    f"- ID interno: {client.id}",
                    f"- Nome: {client.name}",
                    f"- CPF: {client.cpf or 'Não informado'}",
                    f"- Email do cliente: {user_email or 'Não informado'}",
                    f"- Telefone: {client.phone or 'Não informado'}",
                    f"- Celular: {client.mobile_phone or 'Não informado'}",
                    f"- ID Asaas: {client.asaas_id or 'Não informado'}",
                ]
            )

            client_rows = [
                ("ID interno", str(client.id)),
                ("Nome", client.name or "Não informado"),
                ("CPF", client.cpf or "Não informado"),
                ("Email do cliente", user_email or "Não informado"),
                ("Telefone", client.phone or "Não informado"),
                ("Celular", client.mobile_phone or "Não informado"),
                ("ID Asaas", client.asaas_id or "Não informado"),
            ]

            address = getattr(client, "address", None)
            if address:
                address_parts = [
                    f"  Endereço: {address.address or 'Não informado'}",
                    f"  Número: {address.number or 'Não informado'}",
                    f"  Complemento: {address.complement or 'Não informado'}",
                    f"  Bairro: {address.province or 'Não informado'}",
                    f"  Cidade: {address.city or 'Não informado'}",
                    f"  Estado: {address.state or 'Não informado'}",
                    f"  CEP: {address.postal_code or 'Não informado'}",
                ]
                lines.append("Endereço cadastrado:")
                lines.extend(address_parts)
                address_rows = [
                    ("Endereço", address.address or "Não informado"),
                    ("Número", address.number or "Não informado"),
                    ("Complemento", address.complement or "Não informado"),
                    ("Bairro", address.province or "Não informado"),
                    ("Cidade", address.city or "Não informado"),
                    ("Estado", address.state or "Não informado"),
                    ("CEP", address.postal_code or "Não informado"),
                ]
        else:
            lines.append("Nenhum cadastro de cliente encontrado para este usuário.")
            client_rows = [
                ("Status do cadastro", "Nenhum cadastro encontrado para este usuário.")
            ]

        lines.extend(
            [
                "",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "Mensagem enviada automaticamente pela API Pagamento & Frete.",
            ]
        )

        plain_text = "\n".join(lines)

        def _build_html_list(rows: List[Tuple[str, str]]) -> str:
            if not rows:
                return ""
            items = "".join(
                f'<li><span>{escape(label)}</span><strong>{escape(str(value))}</strong></li>'
                for label, value in rows
            )
            return f'<ul class="info-list">{items}</ul>'

        client_block = _build_html_list(client_rows)
        address_block = ""
        if address_rows:
            address_block = (
                '<div class="section">'
                '<div class="section-title subtle">Endereço cadastrado</div>'
                '<div class="card">'
                f"{_build_html_list(address_rows)}"
                "</div>"
                "</div>"
            )
        message_html = "<br>".join(
            part or "&nbsp;" for part in escape(message_text).splitlines()
        )

        now = datetime.now(timezone.utc)
        brand_element, brand_assets = self._build_branding()
        inline_assets: List[EmailService.InlineAsset] = list(brand_assets)

        try:
            html_body = self._render_email_template(
                "contact_message.html",
                {
                    "contact_name": escape(contact_name_value),
                    "contact_email": escape(contact_email_value),
                    "message_html": message_html,
                    "client_block": client_block,
                    "address_block": address_block,
                    "brand_element": brand_element,
                    "year": str(now.year),
                },
            )
        except FileNotFoundError:
            html_body = f"<pre>{escape(plain_text)}</pre>"

        return plain_text, html_body, inline_assets
    
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
            
            text_body, html_body, inline_assets = self._build_order_confirmed_payload(
                order, client
            )

            self._send_email_with_html(
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                recipients=[self.owner_email],
                inline_assets=inline_assets,
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
        shipping_details = self._build_shipping_details(order)
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

FRETE SELECIONADO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{shipping_details}

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

    def _build_order_confirmed_payload(
        self, order: Order, client: Client
    ) -> Tuple[str, str, List["EmailService.InlineAsset"]]:
        """
        Retorna versões texto, HTML e ativos inline para o email de pedido confirmado.
        """
        plain_text = self._build_order_confirmed_message(order, client)
        html_body, inline_assets = self._build_order_confirmed_html(order, client)
        return plain_text, html_body, inline_assets

    def _build_order_confirmed_html(
        self, order: Order, client: Client
    ) -> Tuple[str, List["EmailService.InlineAsset"]]:
        """
        Monta a versão HTML do email de pedido confirmado para o lojista.
        """
        # Produtos
        rows = []
        total_items_qty = 0
        for item in order.items:
            total_items_qty += item.quantity
            rows.append(
                f"<tr>"
                f"<td>{escape(item.product_name)} (ID: {escape(str(item.product_id))})</td>"
                f"<td>{item.quantity}x</td>"
                f"<td>R$ {item.total_price:.2f}</td>"
                f"</tr>"
            )
        items_html = (
            '<table class="items-table">'
            "<thead><tr><th>Produto</th><th>Qtd.</th><th>Total</th></tr></thead>"
            "<tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

        # Endereço
        if client.address:
            complement = (
                f", {client.address.complement}" if client.address.complement else ""
            )
            address_lines = [
                escape(client.name or "Não informado"),
                f"{escape(client.address.address or 'Não informado')}, "
                f"{escape(str(client.address.number or 's/n'))}{escape(complement)}",
                escape(client.address.province or "Bairro não informado"),
                f"{escape(client.address.city or 'Cidade?')} - "
                f"{escape(client.address.state or 'UF?')}",
                f"CEP: {escape(client.address.postal_code or 'Não informado')}",
            ]
            address_html = "<br>".join(address_lines)
        else:
            address_html = "Endereço não informado."

        # Datas e frete
        brazil_tz = pytz.timezone("America/Sao_Paulo")
        confirmed_at_brazil = order.confirmed_at.astimezone(brazil_tz)
        date_str = confirmed_at_brazil.strftime("%d/%m/%Y às %H:%M")

        shipping_details = self._build_shipping_details(order)
        shipping_html = "<br>".join(
            [escape(line) for line in shipping_details.splitlines() if line.strip()]
        )

        brand_element, brand_assets = self._build_branding()
        inline_assets: List[EmailService.InlineAsset] = list(brand_assets)

        context = {
            "brand_element": brand_element,
            "order_reference": escape(order.external_reference or "—"),
            "date_str": date_str,
            "client_name": escape(client.name or "Não informado"),
            "total": f"{order.total:.2f}",
            "total_items": str(total_items_qty),
            "items_html": items_html,
            "shipping_html": shipping_html,
            "address_html": address_html,
        }

        try:
            html_body = self._render_email_template(
                "order_confirmed_owner.html", context
            )
        except FileNotFoundError:
            html_body = f"<pre>{escape(self._build_order_confirmed_message(order, client))}</pre>"
            inline_assets = []

        return html_body, inline_assets
    
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
            
            text_body, html_body, inline_assets = self._build_order_cancelled_payload(
                order, client, refund_info
            )

            self._send_email_with_html(
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                recipients=[self.owner_email],
                inline_assets=inline_assets,
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
        shipping_details = self._build_shipping_details(order)
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DETALHES DO FRETE COTADO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{shipping_details}

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

    def _build_order_cancelled_payload(
        self, order: Order, client: Client, refund_info: List[Dict] = None
    ) -> Tuple[str, str, List["EmailService.InlineAsset"]]:
        plain_text = self._build_order_cancelled_message(order, client, refund_info)
        html_body, inline_assets = self._build_order_cancelled_html(
            order, client, refund_info
        )
        return plain_text, html_body, inline_assets

    def _build_order_cancelled_html(
        self, order: Order, client: Client, refund_info: List[Dict] = None
    ) -> Tuple[str, List["EmailService.InlineAsset"]]:
        # Itens
        rows = []
        total_items_qty = 0
        for item in order.items:
            total_items_qty += item.quantity
            rows.append(
                f"<tr>"
                f"<td>{escape(item.product_name)} (ID: {escape(str(item.product_id))})</td>"
                f"<td>{item.quantity}x</td>"
                f"<td>R$ {item.total_price:.2f}</td>"
                f"</tr>"
            )
        items_html = (
            '<table class="items-table">'
            "<thead><tr><th>Produto</th><th>Qtd.</th><th>Total</th></tr></thead>"
            "<tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

        # Cliente
        customer_rows = [
            ("Nome", client.name or "Não informado"),
            ("CPF", client.cpf or "Não informado"),
            ("Email", (client.email or getattr(client.user, "email", None) or "Não informado")),
            ("Telefone", client.phone or "Não informado"),
            ("Celular", client.mobile_phone or "Não informado"),
        ]

        if client.address:
            complement = (
                f", {client.address.complement}" if client.address.complement else ""
            )
            address_lines = [
                f"{client.address.address or 'Endereço não informado'}, "
                f"{client.address.number or 's/n'}{complement}",
                f"{client.address.province or 'Bairro não informado'}",
                f"{client.address.city or 'Cidade?'} - {client.address.state or 'UF?'}",
                f"CEP: {client.address.postal_code or 'Não informado'}",
            ]
            customer_rows.append(("Endereço", " | ".join(address_lines)))

        customer_info_html = "<ul class=\"info-list\">" + "".join(
            f"<li><span class=\"label\">{escape(label)}</span>"
            f"<span class=\"value\">{escape(str(value))}</span></li>"
            for label, value in customer_rows
        ) + "</ul>"

        # Datas
        brazil_tz = pytz.timezone("America/Sao_Paulo")
        cancelled_at = (
            order.updated_at.astimezone(brazil_tz)
            if order.updated_at
            else datetime.now(timezone.utc).astimezone(brazil_tz)
        )
        cancelled_at_str = cancelled_at.strftime("%d/%m/%Y às %H:%M")
        if order.created_at:
            created_at_brazil = order.created_at.astimezone(brazil_tz)
            created_at_str = created_at_brazil.strftime("%d/%m/%Y às %H:%M")
        else:
            created_at_str = "Não disponível"

        # Frete
        shipping_details = self._build_shipping_details(order)
        shipping_html = "<br>".join(
            [escape(line) for line in shipping_details.splitlines() if line.strip()]
        )

        brand_element, brand_assets = self._build_branding()
        inline_assets: List[EmailService.InlineAsset] = list(brand_assets)

        context = {
            "brand_element": brand_element,
            "order_reference": escape(order.external_reference or "—"),
            "cancelled_at": cancelled_at_str,
            "created_at": created_at_str,
            "total": f"{order.total:.2f}",
            "total_items": str(total_items_qty),
            "customer_info_html": customer_info_html,
            "items_html": items_html,
            "shipping_html": shipping_html,
        }

        try:
            html_body = self._render_email_template(
                "order_cancelled_owner.html", context
            )
        except FileNotFoundError:
            html_body = f"<pre>{escape(self._build_order_cancelled_message(order, client, refund_info))}</pre>"
            inline_assets = []

        return html_body, inline_assets
    
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
            client_email = client.email or (client.user.email if getattr(client, 'user', None) else None)
            if not client_email:
                print("Cliente não possui email cadastrado")
                return False
            
            subject = f"Pedido Cancelado - {order.external_reference}"
            
            text_body, html_body, inline_assets = self._build_order_cancelled_customer_payload(
                order, client
            )

            self._send_email_with_html(
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                recipients=[client_email],
                inline_assets=inline_assets,
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
        shipping_details = self._build_shipping_details(order)
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
FRETE QUE HAVIA SIDO COTADO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{shipping_details}

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
    
    def _build_order_cancelled_customer_payload(
        self, order: Order, client: Client
    ) -> Tuple[str, str, List["EmailService.InlineAsset"]]:
        plain_text = self._build_order_cancelled_customer_message(order, client)

        # Datas
        brazil_tz = pytz.timezone("America/Sao_Paulo")
        cancelled_at = (
            order.updated_at.astimezone(brazil_tz)
            if order.updated_at
            else datetime.now(timezone.utc).astimezone(brazil_tz)
        )
        cancelled_at_str = cancelled_at.strftime("%d/%m/%Y às %H:%M")
        if order.created_at:
            created_at_brazil = order.created_at.astimezone(brazil_tz)
            created_at_str = created_at_brazil.strftime("%d/%m/%Y às %H:%M")
        else:
            created_at_str = "Não disponível"

        # Itens
        rows = []
        total_items_qty = 0
        for item in order.items:
            total_items_qty += item.quantity
            rows.append(
                f"<tr>"
                f"<td>{escape(item.product_name)}</td>"
                f"<td>{item.quantity}x</td>"
                f"<td>R$ {item.total_price:.2f}</td>"
                f"</tr>"
            )
        items_html = (
            '<table class="items-table">'
            "<thead><tr><th>Produto</th><th>Qtd.</th><th>Total</th></tr></thead>"
            "<tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

        shipping_details = self._build_shipping_details(order)
        shipping_html = "<br>".join(
            [escape(line) for line in shipping_details.splitlines() if line.strip()]
        )

        notes_html = escape(order.notes or "Nenhuma observação adicional.")

        brand_element, brand_assets = self._build_branding()
        inline_assets: List[EmailService.InlineAsset] = list(brand_assets)

        context = {
            "brand_element": brand_element,
            "customer_name": escape(client.name or "Cliente"),
            "order_reference": escape(order.external_reference or "—"),
            "created_at": created_at_str,
            "cancelled_at": cancelled_at_str,
            "total": f"{order.total:.2f}",
            "items_html": items_html,
            "shipping_html": shipping_html,
            "notes_html": notes_html,
            "total_items": str(total_items_qty),
        }

        try:
            html_body = self._render_email_template(
                "order_cancelled_customer.html", context
            )
        except FileNotFoundError:
            html_body = f"<pre>{escape(plain_text)}</pre>"
            inline_assets = []

        return plain_text, html_body, inline_assets
    
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
            client_email = client.email or (client.user.email if getattr(client, 'user', None) else None)
            if not client_email:
                print("Cliente não possui email cadastrado")
                return False
            
            subject = f"Estorno Processado - Pedido {order.external_reference}"
            
            text_body, html_body, inline_assets = self._build_refund_customer_payload(
                order, client, payment_info
            )

            self._send_email_with_html(
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                recipients=[client_email],
                inline_assets=inline_assets,
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
        shipping_details = self._build_shipping_details(order)
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
FRETE QUE FOI COTADO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{shipping_details}

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
    
    def _build_refund_customer_payload(
        self, order: Order, client: Client, payment_info: Dict = None
    ) -> Tuple[str, str, List["EmailService.InlineAsset"]]:
        plain_text = self._build_refund_customer_message(order, client, payment_info)

        brazil_tz = pytz.timezone("America/Sao_Paulo")
        refund_at = (
            order.updated_at.astimezone(brazil_tz)
            if order.updated_at
            else datetime.now(timezone.utc).astimezone(brazil_tz)
        )
        refund_at_str = refund_at.strftime("%d/%m/%Y às %H:%M")
        if order.created_at:
            created_at_brazil = order.created_at.astimezone(brazil_tz)
            created_at_str = created_at_brazil.strftime("%d/%m/%Y às %H:%M")
        else:
            created_at_str = "Não disponível"

        rows = []
        total_items_qty = 0
        for item in order.items:
            total_items_qty += item.quantity
            rows.append(
                f"<tr>"
                f"<td>{escape(item.product_name)}</td>"
                f"<td>{item.quantity}x</td>"
                f"<td>R$ {item.total_price:.2f}</td>"
                f"</tr>"
            )
        items_html = (
            '<table class="items-table">'
            "<thead><tr><th>Produto</th><th>Qtd.</th><th>Total</th></tr></thead>"
            "<tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

        shipping_details = self._build_shipping_details(order)
        shipping_html = "<br>".join(
            [escape(line) for line in shipping_details.splitlines() if line.strip()]
        )

        refund_details = []
        if payment_info:
            payment_method = payment_info.get("payment_method")
            if payment_method:
                refund_details.append(("Método de pagamento", payment_method))
            status = payment_info.get("status") or "Processado com sucesso"
            refund_details.append(("Status do estorno", status))
            txn = payment_info.get("transaction_id")
            if txn:
                refund_details.append(("ID da transação", txn))

        if refund_details:
            refund_info_html = "<ul class=\"info-list\">" + "".join(
                f"<li><span class=\"label\">{escape(label)}</span>"
                f"<span class=\"value\">{escape(str(value))}</span></li>"
                for label, value in refund_details
            ) + "</ul>"
        else:
            refund_info_html = "<p style=\"margin:0; font-size:13px; color:#4c4b45;\">Informações adicionais não disponíveis.</p>"

        notes_html = escape(order.notes or "Nenhuma observação adicional.")

        brand_element, brand_assets = self._build_branding()
        inline_assets: List[EmailService.InlineAsset] = list(brand_assets)

        context = {
            "brand_element": brand_element,
            "customer_name": escape(client.name or "Cliente"),
            "order_reference": escape(order.external_reference or "—"),
            "created_at": created_at_str,
            "refund_at": refund_at_str,
            "total": f"{order.total:.2f}",
            "items_html": items_html,
            "shipping_html": shipping_html,
            "refund_info_html": refund_info_html,
            "notes_html": notes_html,
            "total_items": str(total_items_qty),
        }

        try:
            html_body = self._render_email_template(
                "refund_customer.html", context
            )
        except FileNotFoundError:
            html_body = f"<pre>{escape(plain_text)}</pre>"
            inline_assets = []

        return plain_text, html_body, inline_assets
    
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
            
            text_body, html_body, inline_assets = self._build_password_reset_payload(
                user_name=user_name,
                reset_url=reset_url,
                reset_token=reset_token,
            )

            self._send_email_with_html(
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                recipients=[user_email],
                inline_assets=inline_assets,
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

    def _build_password_reset_payload(
        self, user_name: str, reset_url: str, reset_token: str
    ) -> Tuple[str, str, List["EmailService.InlineAsset"]]:
        plain_text = self._build_password_reset_message(user_name, reset_url, reset_token)

        brand_element, brand_assets = self._build_branding()
        inline_assets: List[EmailService.InlineAsset] = list(brand_assets)

        context = {
            "brand_element": brand_element,
            "user_name": escape(user_name or "Cliente"),
            "reset_url": reset_url,
            "reset_token": reset_token,
        }

        try:
            html_body = self._render_email_template(
                "password_reset.html", context
            )
        except FileNotFoundError:
            html_body = f"<pre>{escape(plain_text)}</pre>"
            inline_assets = []

        return plain_text, html_body, inline_assets