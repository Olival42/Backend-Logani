from rest_framework.views import APIView

from api_pagamento_frete.utils import ErrorResponse, SuccessResponse
from modules.email.application.web.serializers import ContactMessageSerializer
from modules.email.domain.services.email_service import EmailService
from modules.usuario.domain.services import UserService
from modules.usuario.adapters.persistence.user_repository_django import UserRepository
from modules.usuario.adapters.persistence.blacklist_repository_django import BlacklistRepository
from modules.cliente.adapters.persistence.client_repository_django import ClientRepository


user_repository = UserRepository()
blacklist_repository = BlacklistRepository()
user_service = UserService(user_repository, blacklist_repository)
client_repository = ClientRepository()
email_service = EmailService()


class ContactMessageView(APIView):
    """
    Endpoint para receber mensagens de contato autenticadas e encaminhar por email.
    """

    def post(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ErrorResponse.unauthorized("Token de acesso não informado.")

        token = auth_header.split(" ")[1]

        try:
            payload = user_service.authenticate(token)
        except ValueError as exc:
            return ErrorResponse.unauthorized(str(exc))

        serializer = ContactMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse.validation_error(serializer.errors)

        user_id = payload.get("user_id")
        client = client_repository.get_by_user_id(str(user_id)) if user_id is not None else None

        contact_data = serializer.validated_data
        email_sent = email_service.send_contact_message(
            contact_name=contact_data["name"],
            contact_email=contact_data["email"],
            message=contact_data["message"],
            client=client,
        )

        if not email_sent:
            return ErrorResponse.internal_server_error("Não foi possível enviar o email de contato.")

        return SuccessResponse.created(
            data={"submitted": True},
            message="Mensagem de contato enviada com sucesso."
        )


