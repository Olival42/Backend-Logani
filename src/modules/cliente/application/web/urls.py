from django.urls import path
from modules.cliente.application.web.views import ClientCreateView, ClientDetailView, ClientUpdateView

urlpatterns = [
    path('register/', ClientCreateView.as_view(), name='client-create'),
    path('<uuid:client_id>/', ClientDetailView.as_view(), name='client-detail'),
    path('<uuid:client_id>/update/', ClientUpdateView.as_view(), name='client-update'),
]