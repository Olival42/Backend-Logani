from rest_framework import serializers
from modules.cliente.domain.entities.client_entity import Client as ClientEntity
from modules.cliente.domain.entities.address_entity import Address as AddressEntity
from modules.cliente.domain.entities.utils.client_validators import ClientValidators
import re

class CreateAddressSerializer(serializers.Serializer):
    address = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "O campo endereço é obrigatório.",
            "blank": "O campo endereço é obrigatório."
        }
    )
    
    number = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "O campo número é obrigatório.",
            "blank": "O campo número é obrigatório."
        }
    )
    
    postal_code = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "O campo CEP é obrigatório.",
            "blank": "O campo CEP é obrigatório."
        }
    )
    
    city = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "O campo cidade é obrigatório.",
            "blank": "O campo cidade é obrigatório."
        }
    )
    
    state = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "O campo estado é obrigatório.",
            "blank": "O campo estado é obrigatório."
        }
    )
    
    complement = serializers.CharField(required=False, allow_blank=True)
    
    province = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "O campo bairro é obrigatório.",
            "blank": "O campo bairro é obrigatório."
        }
    )

    def validate_postal_code(self, value):
        digits = re.sub(r'\D', '', value)
        if len(digits) != 8:
            raise serializers.ValidationError("CEP inválido, deve conter 8 dígitos.")
        return digits

    def validate_state(self, value):
        if len(value.strip()) != 2:
            raise serializers.ValidationError("Estado inválido, deve conter 2 caracteres.")
        return value.strip().upper()

    def validate(self, attrs):
        required_fields = ["address", "number", "postal_code", "city", "state", "province"]
        missing = [f for f in required_fields if not attrs.get(f)]
        if missing:
            raise serializers.ValidationError(
                f"Preencha todos os campos obrigatórios: {', '.join(missing)}."
            )
        return attrs

    def create(self, validated_data):
        try:
            return AddressEntity(**validated_data)
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class CreateClientSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    
    # Campo name removido - será obtido do usuário autenticado
    
    cpf = serializers.CharField(
        required=True, 
        allow_blank=False, 
        error_messages={
            "required": "O campo CPF é obrigatório.",
            "blank": "O campo CPF é obrigatório."
        }
    )
    
    phone = serializers.CharField(required=False, allow_blank=True)
    
    mobile_phone = serializers.CharField(
        required=True, 
        allow_blank=False,
        error_messages={
            "required": "O campo celular é obrigatório.",
            "blank": "O campo celular é obrigatório."
        }
    )
    
    address = CreateAddressSerializer()
    
    asaas_id = serializers.CharField(required=False, allow_blank=True)

    def validate_cpf_cnpj(self, value):
        try:
            return ClientValidators.validate_cpf(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def validate_phone(self, value):
        try:
            return ClientValidators.validate_phone(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def validate_mobile_phone(self, value):
        try:
            return ClientValidators.validate_mobile_phone(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def create(self, validated_data):
        address_data = validated_data.pop("address", {})
        address_entity = CreateAddressSerializer().create(address_data)
        # O nome será obtido do usuário autenticado no serviço
        return ClientEntity(address=address_entity, **validated_data, user=self.context["request"].user)

class UpdateAddressSerializer(serializers.Serializer):
    address = serializers.CharField(required=False)
    number = serializers.CharField(required=False)
    postal_code = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    complement = serializers.CharField(required=False, allow_blank=True)
    province = serializers.CharField(required=False)

class UpdateClientSerializer(serializers.Serializer):
    # Campo name removido - será obtido do usuário autenticado
    cpf = serializers.CharField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    mobile_phone = serializers.CharField(required=False)
    address = UpdateAddressSerializer(required=False)
    asaas_id = serializers.CharField(required=False, allow_blank=True)

    def validate_cpf(self, value):
        try:
            return ClientValidators.validate_cpf(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def validate_phone(self, value):
        try:
            return ClientValidators.validate_phone(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def validate_mobile_phone(self, value):
        try:
            return ClientValidators.validate_mobile_phone(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))