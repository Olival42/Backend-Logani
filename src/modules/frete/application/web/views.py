from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework import renderers
from typing import Dict, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse
from modules.frete.application.web.serializers import (
    ShippingCalculationSerializer,
    ShippingQuoteSerializer,
    AuthTokenSerializer,
    RefreshTokenSerializer
)
from modules.frete.domain.services.melhor_envio_auth_service import MelhorEnvioAuthService
from modules.frete.domain.services.shipping_service import ShippingService
from modules.frete.domain.services.product_mock_service import ProductMockService
from modules.frete.domain.repositories.token_repository import ITokenRepository
from modules.frete.adapters.persistence.token_repository_django import TokenRepositoryDjango
from modules.frete.adapters.external.melhor_envio_client import MelhorEnvioClient


class MelhorEnvioAuthUrlView(APIView):
    """
    View para gerar URL de autorização OAuth do Melhor Envio
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Gera a URL de autorização OAuth do Melhor Envio
        
        GET /shippings/auth/url/
        Query params (opcionais):
        - redirect_uri: URI de redirecionamento (usa o padrão se não informado)
        - state: String para prevenção de CSRF (opcional)
        """
        client_id = getattr(settings, 'MELHOR_ENVIO_CLIENT_ID', None)
        redirect_uri = request.query_params.get('redirect_uri') or getattr(settings, 'MELHOR_ENVIO_REDIRECT_URI', None)
        state = request.query_params.get('state', '')
        
        if not client_id:
            return Response(
                {'error': 'MELHOR_ENVIO_CLIENT_ID não configurado'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if not redirect_uri:
            return Response(
                {'error': 'redirect_uri deve ser informado ou configurado em MELHOR_ENVIO_REDIRECT_URI'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Determina se está em sandbox ou produção
        env = getattr(settings, 'MELHOR_ENVIO_ENVIRONMENT', 'sandbox')
        # URL de autorização OAuth é diferente da URL da API
        if env == 'sandbox':
            auth_url = 'https://sandbox.melhorenvio.com.br/oauth/authorize'
        else:
            # Em produção, pode usar a URL padrão ou auth.melhorenvio.com.br
            auth_url = 'https://auth.melhorenvio.com.br/oauth/authorize'
        
        # Constrói a URL de autorização
        import urllib.parse
        # Escopos mínimos necessários para cálculo de frete
        # Ver documentação: https://docs.melhorenvio.com.br/docs/autenticacao
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'shipping-calculate shipping-companies',  # Escopos mínimos para cálculo de frete
        }
        
        if state:
            params['state'] = state
        
        auth_url_with_params = f"{auth_url}?{urllib.parse.urlencode(params)}"
        
        return Response({
            'auth_url': auth_url_with_params,
            'instructions': 'Redirecione o usuário para esta URL. Após autorização, você receberá um código na URL de callback.'
        }, status=status.HTTP_200_OK)


class MelhorEnvioCallbackView(APIView):
    """
    View para receber o callback do OAuth do Melhor Envio
    """
    permission_classes = [AllowAny]
    renderer_classes = [renderers.JSONRenderer]  # Força retorno JSON sempre
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = MelhorEnvioClient()
        self.token_repository: ITokenRepository = TokenRepositoryDjango()
        self.auth_service = MelhorEnvioAuthService(self.token_repository, self.client)
    
    def get(self, request):
        """
        Recebe o callback do OAuth e processa automaticamente o código
        
        GET /shippings/callback/?code=CODIGO&state=...
        """
        try:
            code = request.query_params.get('code')
            error = request.query_params.get('error')
            error_description = request.query_params.get('error_description')
            
            if error:
                return Response({
                    'error': error,
                    'error_description': error_description,
                    'message': 'Erro ao autorizar aplicação. Verifique os escopos e credenciais.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not code:
                return Response({
                    'error': 'Código de autorização não fornecido'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obtém o redirect_uri usado na requisição original
            redirect_uri = request.query_params.get('redirect_uri') or getattr(settings, 'MELHOR_ENVIO_REDIRECT_URI', None)
            
            # Trocando código por token automaticamente
            token = self.auth_service.authenticate_with_code(code, redirect_uri)
            
            # Verifica se o token foi salvo corretamente
            # Busca diretamente no banco (ignorando o .env) para verificar se foi salvo
            from modules.frete.adapters.persistence.models import MelhorEnvioToken as MelhorEnvioTokenModel
            try:
                saved_model = MelhorEnvioTokenModel.objects.latest('created_at')
                # Verifica se o token salvo corresponde ao token retornado
                if saved_model.access_token != token.access_token:
                    return Response({
                        'error': 'Token não foi salvo corretamente',
                        'message': f'O token foi gerado mas não corresponde ao salvo no banco. Token gerado: {token.access_token[:20]}..., Token salvo: {saved_model.access_token[:20]}...'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Verifica se o refresh_token foi salvo
                if not saved_model.refresh_token or len(saved_model.refresh_token) == 0:
                    return Response({
                        'error': 'Refresh token não foi salvo',
                        'message': 'O token foi salvo mas o refresh_token está vazio. Isso pode indicar um problema na resposta da API.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except MelhorEnvioTokenModel.DoesNotExist:
                return Response({
                    'error': 'Token não foi salvo no banco de dados',
                    'message': 'O token foi gerado mas não foi persistido no banco de dados'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            response_serializer = RefreshTokenSerializer({
                'access_token': token.access_token,
                'refresh_token': token.refresh_token,
                'expires_in': token.expires_in,
                'token_type': token.token_type
            })
            
            return Response({
                'success': True,
                'message': 'Autenticação realizada com sucesso! Token salvo automaticamente.',
                'token': response_serializer.data,
                'saved': True,
                'token_preview': f"{token.access_token[:20]}...{token.access_token[-10:]}" if len(token.access_token) > 30 else "***"
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'error': str(e),
                'message': 'Erro ao processar código de autorização'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            return Response({
                'error': f'Erro ao autenticar: {str(e)}',
                'message': 'Erro interno ao processar autenticação',
                'traceback': traceback.format_exc() if getattr(settings, 'DEBUG', False) else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MelhorEnvioAuthView(APIView):
    """
    View para autenticação OAuth do Melhor Envio
    """
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = MelhorEnvioClient()
        self.token_repository: ITokenRepository = TokenRepositoryDjango()
        self.auth_service = MelhorEnvioAuthService(self.token_repository, self.client)
    
    def post(self, request):
        """
        Autentica usando código de autorização
        
        POST /shippings/auth/
        Body: {
            "authorization_code": "codigo_retornado_pelo_oauth",
            "redirect_uri": "https://seu-site.com/callback"  # opcional
        }
        """
        serializer = AuthTokenSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Dados inválidos', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            authorization_code = serializer.validated_data['authorization_code']
            redirect_uri = serializer.validated_data.get('redirect_uri')
            
            # Valida se client_id e client_secret estão configurados
            client_id = getattr(settings, 'MELHOR_ENVIO_CLIENT_ID', None)
            client_secret = getattr(settings, 'MELHOR_ENVIO_CLIENT_SECRET', None)
            
            if not client_id or not client_id.strip():
                return Response(
                    {'error': 'MELHOR_ENVIO_CLIENT_ID não configurado ou vazio no .env'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            if not client_secret or not client_secret.strip():
                return Response(
                    {'error': 'MELHOR_ENVIO_CLIENT_SECRET não configurado ou vazio no .env'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Informações de debug (sem expor valores completos)
            client_id_preview = f"{client_id[:5]}...{client_id[-3:]}" if len(client_id) > 8 else "***"
            client_secret_preview = f"{client_secret[:5]}...{client_secret[-3:]}" if len(client_secret) > 8 else "***"
            
            try:
                token = self.auth_service.authenticate_with_code(authorization_code, redirect_uri)
            except ValueError as e:
                error_msg = str(e)
                # Adiciona informações de debug se disponível
                if getattr(settings, 'DEBUG', False):
                    error_msg += f" | Client ID: {client_id_preview} | Client Secret: {client_secret_preview}"
                raise ValueError(error_msg)
            
            response_serializer = RefreshTokenSerializer({
                'access_token': token.access_token,
                'refresh_token': token.refresh_token,
                'expires_in': token.expires_in,
                'token_type': token.token_type
            })
            
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            return Response(
                {
                    'error': f'Erro ao autenticar: {str(e)}',
                    'traceback': traceback.format_exc() if getattr(settings, 'DEBUG', False) else None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MelhorEnvioRefreshTokenView(APIView):
    """
    View para renovar token do Melhor Envio
    """
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = MelhorEnvioClient()
        self.token_repository: ITokenRepository = TokenRepositoryDjango()
        self.auth_service = MelhorEnvioAuthService(self.token_repository, self.client)
    
    def post(self, request):
        """
        Renova o token de acesso
        
        POST /shippings/auth/refresh/
        """
        try:
            token = self.auth_service.refresh_access_token()
            
            response_serializer = RefreshTokenSerializer({
                'access_token': token.access_token,
                'refresh_token': token.refresh_token,
                'expires_in': token.expires_in,
                'token_type': token.token_type
            })
            
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Erro ao renovar token: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ShippingCalculationView(APIView):
    """
    View para cálculo de frete
    """
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = MelhorEnvioClient()
        self.token_repository: ITokenRepository = TokenRepositoryDjango()
        self.auth_service = MelhorEnvioAuthService(self.token_repository, self.client)
        self.product_service = ProductMockService()
        self.shipping_service = ShippingService(
            self.auth_service,
            self.client,
            self.product_service
        )
    
    def post(self, request):
        """
        Calcula frete baseado em produtos ou pedido
        
        POST /shippings/calculate/
        
        Opção 1: Com produtos diretamente
        Body: {
            "to_postal_code": "01018020",
            "products": [
                {"product_id": "1", "quantity": 2},
                {"product_id": "2", "quantity": 1}
            ],
            "from_postal_code": "96020360",  # opcional, usa OWNER_CEP do .env se não informado
            "receipt": false,  # opcional
            "own_hand": false,  # opcional
            "services": "1,2,18"  # opcional
        }
        
        Opção 2: Com order_id (busca produtos do pedido automaticamente)
        Body: {
            "to_postal_code": "01018020",
            "order_id": "uuid-do-pedido",
            "from_postal_code": "96020360",  # opcional, usa OWNER_CEP do .env se não informado
            "receipt": false,  # opcional
            "own_hand": false,  # opcional
            "services": "1,2,18"  # opcional
        }
        """
        serializer = ShippingCalculationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Dados inválidos', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Obtém CEP de origem: usa o enviado ou o do .env
            from_postal_code = serializer.validated_data.get('from_postal_code')
            if not from_postal_code:
                from_postal_code = getattr(settings, 'OWNER_CEP', None)
                if not from_postal_code:
                    return Response(
                        {'error': 'CEP de origem não informado. Configure OWNER_CEP no .env ou envie from_postal_code na requisição.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Valida e limpa o CEP de origem (remove formatação)
            from_postal_code = ''.join(filter(str.isdigit, str(from_postal_code)))
            if len(from_postal_code) != 8:
                return Response(
                    {'error': f'CEP de origem inválido. Deve ter 8 dígitos. CEP recebido: {from_postal_code[:10]}...' if len(from_postal_code) > 10 else f'CEP de origem inválido. Deve ter 8 dígitos. Recebido: {len(from_postal_code)} dígitos.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            to_postal_code = serializer.validated_data['to_postal_code']
            order_id = serializer.validated_data.get('order_id')
            
            # Se order_id foi fornecido, busca produtos do pedido
            if order_id:
                from modules.pedido.adapters.persistence.order_repository_django import OrderRepository
                
                order_repository = OrderRepository()
                order = order_repository.get_by_id(order_id)
                
                if not order:
                    return Response(
                        {'error': f'Pedido com ID {order_id} não encontrado'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Extrai produtos do pedido no formato esperado
                products_input = [
                    {
                        'product_id': item.product_id,
                        'quantity': item.quantity
                    }
                    for item in order.items
                ]
                
                if not products_input or len(products_input) == 0:
                    return Response(
                        {'error': f'Pedido {order_id} não possui produtos'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Usa produtos fornecidos diretamente
                products_input = serializer.validated_data.get('products', [])
            
            # Prepara opções
            options = {}
            if serializer.validated_data.get('receipt'):
                options['receipt'] = True
            if serializer.validated_data.get('own_hand'):
                options['own_hand'] = True
            
            services = serializer.validated_data.get('services')
            
            # Calcula frete
            quotes = self.shipping_service.calculate_shipping(
                from_postal_code=from_postal_code,
                to_postal_code=to_postal_code,
                products_input=products_input,
                options=options if options else None,
                services=services
            )
            
            # Serializa resposta
            quotes_serializer = ShippingQuoteSerializer(quotes, many=True)
            
            response_data = {
                'quotes': quotes_serializer.data,
                'count': len(quotes)
            }
            
            # Adiciona informação sobre origem dos produtos se foi usado order_id
            if order_id:
                response_data['order_id'] = order_id
                response_data['products_source'] = 'order'
            else:
                response_data['products_source'] = 'direct'
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Erro ao calcular frete: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MelhorEnvioTokenStatusView(APIView):
    """
    View para verificar status do token (debug)
    """
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.token_repository: ITokenRepository = TokenRepositoryDjango()
        self.auth_service = MelhorEnvioAuthService(
            self.token_repository,
            MelhorEnvioClient()
        )
    
    def get(self, request):
        """
        Verifica status do token
        
        GET /shippings/auth/status/
        """
        from django.conf import settings
        
        # Verifica token no .env
        token_env = getattr(settings, 'MELHOR_ENVIO_ACCESS_TOKEN', None)
        
        # Verifica token no banco (ignorando o .env temporariamente)
        from modules.frete.adapters.persistence.models import MelhorEnvioToken as MelhorEnvioTokenModel
        token_db_raw = None
        try:
            token_model = MelhorEnvioTokenModel.objects.latest('created_at')
            token_db_raw = {
                'access_token': token_model.access_token,
                'refresh_token': token_model.refresh_token,
                'expires_in': token_model.expires_in,
                'token_type': token_model.token_type,
                'created_at': token_model.created_at
            }
        except MelhorEnvioTokenModel.DoesNotExist:
            pass
        
        # Verifica token no banco (com prioridade do .env)
        token_db = self.token_repository.get_latest()
        
        # Verifica token válido
        token_valid = None
        try:
            token_valid = self.auth_service.get_valid_token()
        except Exception as e:
            pass
        
        # Mostra primeiros e últimos caracteres do token (sem expor o token completo)
        token_preview = None
        if token_env:
            if len(token_env) > 10:
                token_preview = f"{token_env[:5]}...{token_env[-5:]}"
            else:
                token_preview = "***"
        
        # Verifica se há token no banco com mais detalhes
        token_db_details = None
        if token_db_raw:
            token_db_details = {
                'has_access_token': bool(token_db_raw['access_token']),
                'has_refresh_token': bool(token_db_raw['refresh_token']) and len(token_db_raw['refresh_token']) > 0,
                'access_token_length': len(token_db_raw['access_token']) if token_db_raw['access_token'] else 0,
                'refresh_token_length': len(token_db_raw['refresh_token']) if token_db_raw['refresh_token'] else 0,
                'expires_in': token_db_raw['expires_in'],
                'created_at': token_db_raw['created_at'].isoformat() if token_db_raw['created_at'] else None,
                'is_expired': (timezone.now() >= (token_db_raw['created_at'] + timedelta(seconds=token_db_raw['expires_in']))) if token_db_raw['created_at'] else None,
                'source': 'oauth' if token_db_raw['refresh_token'] else 'env_or_manual'
            }
        elif token_db:
            token_db_details = {
                'has_access_token': bool(token_db.access_token),
                'has_refresh_token': bool(token_db.refresh_token) and len(token_db.refresh_token) > 0,
                'access_token_length': len(token_db.access_token) if token_db.access_token else 0,
                'refresh_token_length': len(token_db.refresh_token) if token_db.refresh_token else 0,
                'expires_in': token_db.expires_in,
                'created_at': token_db.created_at.isoformat() if token_db.created_at else None,
                'is_expired': token_db.is_expired() if token_db.created_at else None,
                'source': 'env' if token_env else 'oauth'
            }
        
        # Determina a origem do token
        token_source = 'unknown'
        if token_env and token_db_raw and token_env == token_db_raw.get('access_token'):
            token_source = 'env_file'
        elif token_db_raw and token_db_raw.get('refresh_token'):
            token_source = 'oauth'
        elif token_db_raw:
            token_source = 'manual_or_legacy'
        
        # Mensagem sobre refresh_token
        refresh_token_message = None
        if token_db_details and not token_db_details.get('has_refresh_token'):
            refresh_token_message = 'Token não possui refresh_token. Para renovar automaticamente, autorize o app via OAuth novamente.'
        
        return Response({
            'token_in_env': bool(token_env),
            'token_env_length': len(token_env) if token_env else 0,
            'token_env_preview': token_preview,
            'token_in_db': bool(token_db),
            'token_db_details': token_db_details,
            'token_valid': bool(token_valid),
            'token_access_token_length': len(token_valid.access_token) if token_valid and token_valid.access_token else 0,
            'token_source': token_source,
            'can_refresh': token_db_details.get('has_refresh_token', False) if token_db_details else False,
            'refresh_token_message': refresh_token_message,
            'environment': getattr(settings, 'MELHOR_ENVIO_ENVIRONMENT', 'sandbox'),
            'base_url': 'https://sandbox.melhorenvio.com.br' if getattr(settings, 'MELHOR_ENVIO_ENVIRONMENT', 'sandbox') == 'sandbox' else 'https://melhorenvio.com.br',
            'client_id_configured': bool(getattr(settings, 'MELHOR_ENVIO_CLIENT_ID', None)),
            'client_secret_configured': bool(getattr(settings, 'MELHOR_ENVIO_CLIENT_SECRET', None)),
            'redirect_uri_configured': bool(getattr(settings, 'MELHOR_ENVIO_REDIRECT_URI', None)),
            'instructions': {
                'env_var_name': 'ACESS_TOKEN_MELHOR_ENVIO',
                'how_to_copy': 'Copie apenas o valor do token (sem "Bearer" ou espaços)',
                'where_to_copy': 'No painel do Melhor Envio, clique no token e copie o valor',
                'restart_required': 'Reinicie o servidor após adicionar o token no .env',
                'about_app_list': 'O aplicativo pode não aparecer imediatamente na lista "Aplicativos autorizados". Isso é normal e não afeta o funcionamento. O importante é que o token funcione.',
                'about_refresh_token': 'Tokens gerados manualmente não têm refresh_token. Para ter renovação automática, autorize via OAuth (fluxo completo).'
            }
        }, status=status.HTTP_200_OK)
