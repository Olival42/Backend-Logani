from django.db import models
from django.utils import timezone

class User(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    password = models.CharField(max_length=255)
    registration_date = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'users'


class PasswordResetToken(models.Model):
    """
    Modelo para armazenar tokens de reset de senha
    Token é armazenado como hash para segurança
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token_hash = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"PasswordResetToken for {self.user.email} - {'Used' if self.used else 'Active'}"
    
    def is_expired(self):
        """Verifica se o token expirou"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Verifica se o token é válido (não usado e não expirado)"""
        return not self.used and not self.is_expired()
    
    class Meta:
        db_table = 'password_reset_tokens'
        indexes = [
            models.Index(fields=['token_hash']),
            models.Index(fields=['user', 'used', 'expires_at']),
        ]