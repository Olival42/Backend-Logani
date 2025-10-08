from django.db import models
from modules.usuario.adapters.persistence.models import User

class Address(models.Model):
    address = models.CharField(max_length=255)
    address_number = models.CharField(max_length=10)
    complement = models.CharField(max_length=255, blank=True, null=True)
    province = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=2)
    postal_code = models.CharField(max_length=8)

    class Meta:
        db_table = "addresses"

    def __str__(self):
        return f"{self.address}, {self.address_number} - {self.city}/{self.state}"


class Client(models.Model):
    
    TYPE_PERSON_CHOICES = [
        ("PF", "Pessoa Física"),
        ("PJ", "Pessoa Jurídica"),
    ]
    
    type_person = models.CharField(
        max_length=2,
        choices=TYPE_PERSON_CHOICES,
        verbose_name="Tipo de pessoa"
    )

    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="client"
    )
    cpf_cnpj = models.CharField(max_length=14, unique=True)
    phone = models.CharField(max_length=11, blank=True, null=True)
    mobile_phone = models.CharField(max_length=11, blank=True, null=True)

    address = models.OneToOneField(
        Address,
        on_delete=models.SET_NULL,
        related_name="client",
        null=True,
        blank=True
    )
    
    state_register = models.CharField(max_length=255, blank=True, null=True)

    registration_date = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    
    asaas_id = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "clients"

    def __str__(self):
        return self.name