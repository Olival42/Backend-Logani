from django.urls import path, include

urlpatterns = [
    path('', include('modules.cliente.application.web.asaas_urls')),
]