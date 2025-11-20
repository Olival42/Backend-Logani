from typing import List, Optional, Dict
from decimal import Decimal
from modules.frete.domain.entities.product_entity import Product
from api_pagamento_frete.utils import produto_repository, Produto


class ProductMockService:
    """
    Serviço para buscar produtos mockados usando o ProdutoRepository do utils.py
    """
    
    @staticmethod
    def get_product(product_id: str) -> Optional[Product]:
        """
        Busca um produto pelo ID usando o repositório mockado
        
        Args:
            product_id: ID do produto
            
        Returns:
            Product ou None se não encontrado
        """
        produto = produto_repository.get_by_id(product_id)
        
        if not produto:
            return None
        
        # Converte Produto do utils.py para Product da entidade de domínio
        return Product(
            id=produto.id,
            width=produto.largura,  # largura em cm
            height=produto.altura,   # altura em cm
            length=produto.comprimento,  # comprimento em cm
            weight=produto.peso,  # peso em kg
            insurance_value=produto.preco,  # usa o preço como valor para seguro
            quantity=1
        )
    
    @staticmethod
    def get_products(product_ids_with_quantities: List[Dict[str, int]]) -> List[Product]:
        """
        Busca múltiplos produtos com suas quantidades
        
        Args:
            product_ids_with_quantities: Lista de dicts com {"product_id": "1", "quantity": 2}
            
        Returns:
            Lista de Products com quantidades definidas
        """
        products = []
        
        for item in product_ids_with_quantities:
            product_id = str(item.get("product_id") or item.get("id"))
            quantity = item.get("quantity", 1)
            
            product = ProductMockService.get_product(product_id)
            
            if product:
                product.quantity = quantity
                products.append(product)
        
        return products
