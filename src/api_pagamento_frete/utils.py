"""
Utilitários globais para respostas padronizadas da API
"""
from rest_framework.response import Response
from rest_framework import status
from typing import Optional, Dict, Any, List
from datetime import datetime


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

