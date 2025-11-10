from rest_framework import serializers


class ContactMessageSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField(max_length=254)
    message = serializers.CharField(max_length=2000)

    def validate_message(self, value: str) -> str:
        if len(value.strip()) == 0:
            raise serializers.ValidationError("A mensagem não pode estar vazia.")
        return value.strip()


