from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone


class CouponService:
    """
    Serviço mock para validação e aplicação de cupons de desconto
    """
    
    # Mock de cupons disponíveis
    # Em produção, isso viria de um banco de dados
    MOCK_COUPONS = {
        'DESCONTO94': {
            'code': 'DESCONTO94',
            'discount_type': 'PERCENTAGE',  # PERCENTAGE ou FIXED
            'discount_value': Decimal('94.00'),  # 10% ou R$ 10,00
            'min_value': None,  # Valor mínimo do pedido
            'max_discount': None,  # Desconto máximo (para percentual)
            'expires_at': None,  # None = sem expiração
            'active': True,
            'description': 'Desconto de 94%'
        }
    }
    
    def validate_coupon(self, coupon_code: str, order_value: Decimal, client_id: Optional[str] = None) -> Dict:
        """
        Valida um cupom de desconto
        
        Args:
            coupon_code: Código do cupom
            order_value: Valor total do pedido
            client_id: ID do cliente (opcional, necessário para validações de primeira compra)
            
        Returns:
            Dict com informações do cupom válido ou erro
            
        Raises:
            ValueError: Se o cupom for inválido
        """
        if not coupon_code:
            raise ValueError("Código do cupom não informado")
        
        coupon_code = coupon_code.upper().strip()
        
        # Busca o cupom no mock
        coupon = self.MOCK_COUPONS.get(coupon_code)
        
        if not coupon:
            raise ValueError(f"Cupom '{coupon_code}' não encontrado")
        
        if not coupon['active']:
            raise ValueError(f"Cupom '{coupon_code}' está inativo")
        
        # Verifica expiração
        if coupon['expires_at']:
            expires_at = coupon['expires_at']
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if expires_at < timezone.now():
                raise ValueError(f"Cupom '{coupon_code}' expirado")
        
        # Verifica valor mínimo
        min_value = coupon.get('min_value')
        if min_value is not None:
            min_value_decimal = min_value if isinstance(min_value, Decimal) else Decimal(str(min_value))
            if order_value < min_value_decimal:
                raise ValueError(
                    f"Valor mínimo do pedido para usar este cupom é R$ {min_value_decimal:.2f}"
                )
        max_discount = coupon.get('max_discount')
        if max_discount is not None and not isinstance(max_discount, Decimal):
            coupon['max_discount'] = Decimal(str(max_discount))
        
        # Validação especial para DESCONTO10: apenas primeira compra
        if coupon_code == 'DESCONTO94' and client_id:
            if not self._is_first_purchase(client_id):
                raise ValueError(
                    "O cupom DESCONTO94 é válido apenas para a primeira compra. "
                    "Você já possui compras anteriores."
                )
        
        return coupon
    
    def _is_first_purchase(self, client_id: str, exclude_order_id: Optional[str] = None) -> bool:
        """
        Verifica se é a primeira compra do cliente
        
        Args:
            client_id: ID do cliente
            exclude_order_id: ID do pedido a ser excluído da verificação (opcional)
            
        Returns:
            True se for a primeira compra, False caso contrário
        """
        try:
            from modules.pedido.adapters.persistence.order_repository_django import OrderRepository
            order_repository = OrderRepository()
            
            # Busca todos os pedidos do cliente
            client_orders = order_repository.get_by_client(client_id)
            
            # Verifica se existe algum pedido pago ou confirmado
            # Considera apenas pedidos que foram realmente finalizados (PAID ou CONFIRMED)
            # Exclui o pedido atual se fornecido
            for order in client_orders:
                # Ignora o pedido atual se fornecido
                if exclude_order_id and str(order.id) == exclude_order_id:
                    continue
                    
                # Se encontrou algum pedido pago ou confirmado, não é primeira compra
                if order.status in ['PAID', 'CONFIRMED']:
                    return False
            
            # Se não encontrou nenhum pedido pago/confirmado, é a primeira compra
            return True
            
        except Exception:
            # Em caso de erro ao verificar, permite o uso do cupom (fail-safe)
            # Em produção, pode querer logar o erro
            return True
    
    def calculate_discount(self, coupon_code: str, order_value: Decimal, client_id: Optional[str] = None) -> Dict:
        """
        Calcula o desconto aplicável baseado no cupom
        
        Args:
            coupon_code: Código do cupom
            order_value: Valor total do pedido
            client_id: ID do cliente (opcional, necessário para validações de primeira compra)
            
        Returns:
            Dict com:
                - discount_amount: Valor do desconto calculado
                - final_value: Valor final após desconto
                - coupon_info: Informações do cupom
        """
        coupon = self.validate_coupon(coupon_code, order_value, client_id)
        
        discount_amount = Decimal('0.00')
        
        if coupon['discount_type'] == 'PERCENTAGE':
            # Calcula desconto percentual
            discount_amount = (order_value * coupon['discount_value']) / Decimal('100.00')
            
            # Aplica limite máximo se existir
            if coupon['max_discount']:
                discount_amount = min(discount_amount, coupon['max_discount'])
        elif coupon['discount_type'] == 'FIXED':
            # Desconto fixo
            discount_amount = coupon['discount_value']
        
        # Garante que o desconto não seja maior que o valor do pedido
        discount_amount = min(discount_amount, order_value)
        
        # Calcula valor final
        final_value = order_value - discount_amount
        
        # Garante que o valor final não seja negativo
        if final_value < Decimal('0.00'):
            final_value = Decimal('0.00')
            discount_amount = order_value
        
        return {
            'discount_amount': discount_amount,
            'final_value': final_value,
            'coupon_info': {
                'code': coupon['code'],
                'description': coupon['description'],
                'discount_type': coupon['discount_type'],
                'original_value': order_value
            }
        }

