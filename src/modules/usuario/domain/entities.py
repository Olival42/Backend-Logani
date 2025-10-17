import re
import bcrypt
from datetime import datetime, timezone

class User:
    def __init__(self, id, name: str, email: str, password: str, registration_date=None, active=True, _is_hashed=False):
        if not name or not email or not password:
            raise ValueError("Todos os campos são obrigatórios")
        self.id = id
        self.name = name
        self.active = active
        self.registration_date = registration_date or datetime.now(timezone.utc)

        self.set_email(email)
        if _is_hashed:
            self.password = password
        else:
            self.set_password(password)

    def set_email(self, email: str):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Email inválido")
        self.email = email

    def set_password(self, password: str):
        if len(password) < 8:
            raise ValueError("Senha precisa ter pelo menos 8 caracteres")
        if not re.search(r"[A-Z]", password):
            raise ValueError("Senha precisa ter pelo menos uma letra maiúscula")
        if not re.search(r"\d", password):
            raise ValueError("Senha precisa ter pelo menos um número")
        if not re.search(r"\W", password):
            raise ValueError("Senha precisa ter pelo menos um caractere especial")
        self.password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())