"""
Utilitários globais para respostas padronizadas da API
"""
from rest_framework.response import Response
from rest_framework import status
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Produto:
    """
    Classe que representa um produto com suas dimensões e peso
    """
    id: str
    nome: str
    preco: Decimal = Decimal('0.00')
    largura: Decimal = Decimal('0.00')
    comprimento: Decimal = Decimal('0.00')
    altura: Decimal = Decimal('0.00')
    peso: Decimal = Decimal('0.00')
    imagem: str = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o produto para dicionário
        """
        return {
            'id': self.id,
            'nome': self.nome,
            'preco': float(self.preco),
            'largura': float(self.largura),
            'comprimento': float(self.comprimento),
            'altura': float(self.altura),
            'peso': float(self.peso),
            'imagem': self.imagem
        }


class ProdutoRepository:
    """
    Singleton para gerenciar produtos mockados globalmente
    """
    _instance = None
    _produtos = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProdutoRepository, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._produtos = [
                Produto(
                    id='1',
                    nome='Notebook Dell XPS 15',
                    preco=Decimal('120.00'),
                    largura=Decimal('25.00'),
                    comprimento=Decimal('25.00'),
                    altura=Decimal('25.00'),
                    peso=Decimal('500.00'),
                    imagem="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"
                ),
                Produto(
                    id='2',
                    nome='Smartphone Samsung Galaxy S23',
                    preco=Decimal('120.00'),
                    largura=Decimal('25.00'),
                    comprimento=Decimal('25.00'),
                    altura=Decimal('25.00'),
                    peso=Decimal('500.00'),
                    imagem="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"
                ),
                Produto(
                    id='3',
                    nome='Monitor LG UltraWide 34"',
                    preco=Decimal('120.00'),
                    largura=Decimal('25.00'),
                    comprimento=Decimal('25.00'),
                    altura=Decimal('25.00'),
                    peso=Decimal('500.00'),
                    imagem="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"
                )
            ]
            self._initialized = True
    
    def get_all(self) -> List[Produto]:
        """
        Retorna todos os produtos
        """
        return self._produtos
    
    def get_by_id(self, produto_id: str) -> Optional[Produto]:
        """
        Retorna um produto pelo ID
        """
        for produto in self._produtos:
            if produto.id == produto_id:
                return produto
        return None
    
    def get_by_ids(self, produto_ids: List[str]) -> List[Produto]:
        """
        Retorna produtos pelos IDs fornecidos
        """
        return [produto for produto in self._produtos if produto.id in produto_ids]


# Instância global para acesso fácil
produto_repository = ProdutoRepository()


class ErrorResponse:
    """
    Classe utilitária para criar respostas de erro padronizadas
    """
    
    @staticmethod
    def unauthorized(message: str = "Token não informado") -> Response:
        """
        Retorna erro de autenticação/autorização (401)
        
        Args:
            message: Mensagem de erro
            
        Returns:
            Response com status 401
        """
        return Response(
            {
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def bad_request(message: str, details: Optional[Dict[str, Any]] = None) -> Response:
        """
        Retorna erro de requisição inválida (400)
        
        Args:
            message: Mensagem de erro
            details: Detalhes adicionais do erro (ex: erros de validação)
            
        Returns:
            Response com status 400
        """
        error_data = {
            "error": {
                "code": "BAD_REQUEST",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        if details:
            error_data["error"]["details"] = details
        
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
    
    @staticmethod
    def validation_error(errors: Dict[str, Any]) -> Response:
        """
        Retorna erro de validação (400)
        
        Args:
            errors: Dicionário com erros de validação (geralmente de serializers)
            
        Returns:
            Response com status 400
        """
        return Response(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Erro de validação nos dados fornecidos",
                    "details": errors,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @staticmethod
    def not_found(message: str = "Recurso não encontrado") -> Response:
        """
        Retorna erro de recurso não encontrado (404)
        
        Args:
            message: Mensagem de erro
            
        Returns:
            Response com status 404
        """
        return Response(
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def internal_server_error(message: str = "Erro interno do servidor", details: Optional[str] = None) -> Response:
        """
        Retorna erro interno do servidor (500)
        
        Args:
            message: Mensagem de erro
            details: Detalhes adicionais do erro (usado apenas em desenvolvimento)
            
        Returns:
            Response com status 500
        """
        error_data = {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Adiciona detalhes apenas em ambiente de desenvolvimento
        import os
        if details and os.getenv('DEBUG', 'False') == 'True':
            error_data["error"]["details"] = details
        
        return Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @staticmethod
    def forbidden(message: str = "Acesso negado") -> Response:
        """
        Retorna erro de acesso negado (403)
        
        Args:
            message: Mensagem de erro
            
        Returns:
            Response com status 403
        """
        return Response(
            {
                "error": {
                    "code": "FORBIDDEN",
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            status=status.HTTP_403_FORBIDDEN
        )

    @staticmethod
    def custom(status_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Response:
        """
        Retorna um erro customizado
        
        Args:
            status_code: Código HTTP de status
            code: Código de erro customizado
            message: Mensagem de erro
            details: Detalhes adicionais
            
        Returns:
            Response com status customizado
        """
        error_data = {
            "error": {
                "code": code,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        if details:
            error_data["error"]["details"] = details
        
        return Response(error_data, status=status_code)


class SuccessResponse:
    """
    Classe utilitária para criar respostas de sucesso padronizadas
    """
    
    @staticmethod
    def ok(data: Any = None, message: Optional[str] = None) -> Response:
        """
        Retorna resposta de sucesso (200)
        
        Args:
            data: Dados da resposta
            message: Mensagem opcional
            
        Returns:
            Response com status 200
        """
        response_data = {}
        
        if message:
            response_data["message"] = message
        
        if data is not None:
            response_data["data"] = data
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    @staticmethod
    def created(data: Any = None, message: Optional[str] = None) -> Response:
        """
        Retorna resposta de criação bem-sucedida (201)
        
        Args:
            data: Dados da resposta
            message: Mensagem opcional
            
        Returns:
            Response com status 201
        """
        response_data = {}
        
        if message:
            response_data["message"] = message
        
        if data is not None:
            response_data["data"] = data
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @staticmethod
    def no_content() -> Response:
        """
        Retorna resposta sem conteúdo (204)
        
        Returns:
            Response com status 204
        """
        return Response(status=status.HTTP_204_NO_CONTENT)

