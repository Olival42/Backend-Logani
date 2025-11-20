from django.urls import path
from modules.frete.application.web import views

app_name = 'frete'

urlpatterns = [
    path('auth/url/', views.MelhorEnvioAuthUrlView.as_view(), name='auth-url'),
    path('auth/', views.MelhorEnvioAuthView.as_view(), name='auth'),
    path('auth/refresh/', views.MelhorEnvioRefreshTokenView.as_view(), name='auth-refresh'),
    path('auth/status/', views.MelhorEnvioTokenStatusView.as_view(), name='auth-status'),
    path('callback/', views.MelhorEnvioCallbackView.as_view(), name='callback'),
    path('calculate/', views.ShippingCalculationView.as_view(), name='calculate'),
]

