from rest_framework import serializers
from modules.cliente.application.web.serializers import CreateClientSerializer, UpdateClientSerializer


class AsaasCreateClientSerializer(CreateClientSerializer):
    """
    Serializer para criação de clientes com integração ao Asaas
    Herda de CreateClientSerializer e adiciona campos específicos do Asaas
    """
    
    # Campos específicos do Asaas (opcionais)
    email = serializers.EmailField(required=False, allow_blank=True)
    externalReference = serializers.CharField(required=False, allow_blank=True, max_length=100)
    
    def validate_externalReference(self, value):
        """Validação para referência externa"""
        if value and len(value) > 100:
            raise serializers.ValidationError("Referência externa deve ter no máximo 100 caracteres.")
        return value


class AsaasUpdateClientSerializer(UpdateClientSerializer):
    """
    Serializer para atualização de clientes com integração ao Asaas
    Herda de UpdateClientSerializer e adiciona campos específicos do Asaas
    """
    
    # Campos específicos do Asaas (opcionais)
    email = serializers.EmailField(required=False, allow_blank=True)
    externalReference = serializers.CharField(required=False, allow_blank=True, max_length=100)
    
    def validate_externalReference(self, value):
        """Validação para referência externa"""
        if value and len(value) > 100:
            raise serializers.ValidationError("Referência externa deve ter no máximo 100 caracteres.")
        return value


class AsaasSyncSerializer(serializers.Serializer):
    """
    Serializer para sincronização de clientes com o Asaas
    """
    
    client_id = serializers.UUIDField(required=True)
    
    def validate_client_id(self, value):
        """Valida se o cliente existe"""
        from modules.cliente.adapters.persistence.client_repository_django import ClientRepository
        
        repository = ClientRepository()
        try:
            client = repository.get_by_id(str(value))
            if not client:
                raise serializers.ValidationError("Cliente não encontrado.")
            return value
        except Exception:
            raise serializers.ValidationError("Cliente não encontrado.")


class AsaasCustomerResponseSerializer(serializers.Serializer):
    """
    Serializer para resposta da API do Asaas
    """
    
    id = serializers.CharField()
    name = serializers.CharField()
    cpfCnpj = serializers.CharField()
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    mobilePhone = serializers.CharField(required=False)
    address = serializers.CharField(required=False)
    addressNumber = serializers.CharField(required=False)
    complement = serializers.CharField(required=False)
    province = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    postalCode = serializers.CharField(required=False)
    externalReference = serializers.CharField(required=False)
    notificationDisabled = serializers.BooleanField(required=False)
    additionalEmails = serializers.ListField(
        child=serializers.EmailField(),
        required=False
    )
    dateCreated = serializers.DateTimeField(required=False)
    deleted = serializers.BooleanField(required=False)


class AsaasClientListSerializer(serializers.Serializer):
    """
    Serializer para listagem de clientes do Asaas
    """
    
    object = serializers.CharField()
    hasMore = serializers.BooleanField()
    totalCount = serializers.IntegerField()
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()
    data = AsaasCustomerResponseSerializer(many=True)


class AsaasErrorSerializer(serializers.Serializer):
    """
    Serializer para erros da API do Asaas
    """
    
    errors = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    message = serializers.CharField(required=False)
