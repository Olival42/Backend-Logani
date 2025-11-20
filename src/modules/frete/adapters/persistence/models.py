from django.db import models
from django.utils import timezone


class MelhorEnvioToken(models.Model):
    """
    Modelo para armazenar tokens de autenticação do Melhor Envio
    """
    id = models.AutoField(primary_key=True)
    access_token = models.TextField(unique=True)
    refresh_token = models.TextField(unique=True, null=True, blank=True)  # Permite null para tokens manuais
    expires_in = models.IntegerField(default=2592000)  # 30 dias em segundos
    token_type = models.CharField(max_length=50, default='Bearer')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'melhor_envio_token'
        verbose_name = 'Token Melhor Envio'
        verbose_name_plural = 'Tokens Melhor Envio'
    
    def __str__(self):
        return f"Token {self.id} - Criado em {self.created_at}"
    
    def is_expired(self) -> bool:
        """
        Verifica se o token está expirado
        """
        from datetime import timedelta
        expires_at = self.created_at + timedelta(seconds=self.expires_in)
        return timezone.now() >= expires_at

