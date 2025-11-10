"""
URL configuration for api_pagamento_frete project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    return HttpResponse("API Pagamento & Frete rodando 🚀")

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", home),  # rota inicial
    path('users/', include('modules.usuario.application.web.urls')),
    path('clients/', include('modules.cliente.application.web.urls')),
    path('checkouts/', include('modules.checkout.application.web.urls')),
    path('orders/', include('modules.pedido.application.web.urls')),
    path('webhooks/', include('modules.webhook.application.web.urls')),
    path('shippings/', include('modules.frete.urls')),
    path('melhor-envio/', include('modules.frete.urls')),  # Rota alternativa para compatibilidade
    path('emails/', include('modules.email.urls')),
]
