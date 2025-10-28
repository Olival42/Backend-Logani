from django.urls import path
from .asaas_views import (
    AsaasClientCreateView,
    AsaasClientUpdateView,
    AsaasClientSyncView,
    AsaasClientDetailView
)

urlpatterns = [
    path('create/', AsaasClientCreateView.as_view(), name='asaas-client-create'),
    path('update/<str:client_id>/', AsaasClientUpdateView.as_view(), name='asaas-client-update'),
    path('sync/<str:client_id>/', AsaasClientSyncView.as_view(), name='asaas-client-sync'),
    path('detail/<str:client_id>/', AsaasClientDetailView.as_view(), name='asaas-client-detail'),
]
