from django.urls import path
from .asaas_views import (
    AsaasClientCreateView,
    AsaasClientUpdateView,
    AsaasClientSyncView,
    AsaasClientDetailView,
    ClientByBearerTokenView
)

urlpatterns = [
    path('create/', AsaasClientCreateView.as_view(), name='asaas-client-create'),
    path('update/', AsaasClientUpdateView.as_view(), name='asaas-client-update'),
    path('sync/<str:client_id>/', AsaasClientSyncView.as_view(), name='asaas-client-sync'),
    path('detail/<str:client_id>/', AsaasClientDetailView.as_view(), name='asaas-client-detail'),
    path('client-by-bearer-token/', ClientByBearerTokenView.as_view(), name='client-by-bearer-token'),
]
