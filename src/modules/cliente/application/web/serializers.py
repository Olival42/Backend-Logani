from rest_framework import serializers
from modules.cliente.domain.entities.client_entity import Client as ClientEntity
from modules.cliente.domain.entities.address_entity import Address as AddressEntity

class AddressSerializer(serializers.Serializer):
    postal_code = serializers.CharField(required=False, allow_blank=True)
    number = serializers.CharField(required=False, allow_blank=True, max_length=10)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=255, required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    complement = serializers.CharField(max_length=255, required=False, allow_blank=True)
    province = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def create(self, validated_data):
        return AddressEntity(
            address=validated_data["address"],
            number=validated_data["number"],
            postal_code=validated_data["postal_code"],
            city=validated_data["city"],
            state=validated_data["state"],
            complement=validated_data.get("complement", ""),
            province=validated_data.get("province", "")
        )

class ClientSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    type_person = serializers.ChoiceField(choices=["PF", "PJ"], required=False, allow_blank=True)
    cpf_cnpj = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    mobile_phone = serializers.CharField(required=False, allow_blank=True)
    state_register = serializers.CharField(required=False, allow_blank=True)
    address = AddressSerializer()
    asaas_id = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def create(self, validated_data):
        address_data = validated_data.pop("address")
        address_entity = AddressSerializer().create(address_data)

        client_entity = ClientEntity(
            id=validated_data.get("id"),
            name=validated_data["name"],
            cpf_cnpj=validated_data["cpf_cnpj"],
            phone=validated_data.get("phone"),
            mobile_phone=validated_data["mobile_phone"],
            address=address_entity,
            user=self.context["request"].user,
            asaas_id=validated_data.get("asaas_id")
)
        return client_entity
