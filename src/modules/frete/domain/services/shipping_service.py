from typing import List, Optional, Dict
from modules.frete.domain.entities.product_entity import Product
from modules.frete.domain.entities.shipping_quote_entity import ShippingQuote
from modules.frete.domain.services.product_mock_service import ProductMockService
from modules.frete.domain.services.melhor_envio_auth_service import MelhorEnvioAuthService
from modules.frete.adapters.external.melhor_envio_client import MelhorEnvioClient


class ShippingService:
    """
    Serviço para cálculo de frete
    """
    
    def __init__(
        self,
        auth_service: MelhorEnvioAuthService,
        melhor_envio_client: MelhorEnvioClient,
        product_service: ProductMockService = None
    ):
        self.auth_service = auth_service
        self.client = melhor_envio_client
        self.product_service = product_service or ProductMockService()
    
    def calculate_shipping(
        self,
        from_postal_code: str,
        to_postal_code: str,
        products_input: List[Dict[str, int]],  # [{"product_id": "1", "quantity": 2}]
        options: Optional[Dict] = None,
        services: Optional[str] = None
    ) -> List[ShippingQuote]:
        """
        Calcula frete baseado em produtos
        
        Args:
            from_postal_code: CEP de origem (formato: 00000000)
            to_postal_code: CEP de destino (formato: 00000000)
            products_input: Lista de produtos com IDs e quantidades
                           [{"product_id": "1", "quantity": 2}, ...]
            options: Opções adicionais (receipt, own_hand, etc)
            services: IDs dos serviços separados por vírgula (opcional)
            
        Returns:
            Lista de cotações de frete
            
        Raises:
            ValueError: Se não houver token válido ou se houver erro na cotação
        """
        # Obtém token válido
        try:
            token = self.auth_service.ensure_valid_token()
        except ValueError as e:
            raise ValueError(
                f"Não foi possível obter token válido. Verifique se ACESS_TOKEN_MELHOR_ENVIO está configurado no .env. "
                f"Erro: {str(e)}"
            )
        
        if not token or not token.access_token:
            raise ValueError(
                "Token de acesso não disponível. Verifique se ACESS_TOKEN_MELHOR_ENVIO está configurado no .env"
            )
        
        # Busca produtos mockados
        products = self.product_service.get_products(products_input)
        
        if not products:
            raise ValueError("Nenhum produto válido encontrado")
        
        # Converte produtos para formato do Melhor Envio
        products_formatted = [product.to_melhor_envio_format() for product in products]
        
        # Remove espaços e caracteres especiais dos CEPs
        from_postal_code = ''.join(filter(str.isdigit, from_postal_code))
        to_postal_code = ''.join(filter(str.isdigit, to_postal_code))
        
        if len(from_postal_code) != 8:
            raise ValueError("CEP de origem inválido")
        
        if len(to_postal_code) != 8:
            raise ValueError("CEP de destino inválido")
        
        # Calcula frete
        quotes = self.client.calculate_shipping(
            access_token=token.access_token,
            from_postal_code=from_postal_code,
            to_postal_code=to_postal_code,
            products=products_formatted,
            options=options,
            services=services
        )
        
        return quotes

