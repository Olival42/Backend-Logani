from modules.usuario.adapters.persistence.models import User as UserModel
from modules.usuario.domain.entities import User
from modules.usuario.domain.repositories.user_repository import IUserRepository

from modules.usuario.domain.entities import User
from modules.usuario.adapters.persistence.models import User as UserModel

class UserRepository(IUserRepository):
    def save(self, user: User) -> User:
        created_obj, _ = UserModel.objects.update_or_create(
            id=user.id,
            defaults={
                "name": user.name,
                "email": user.email,
                "password": user.password,
                "active": user.active,
            }
        )
        return User(
            id=created_obj.id,
            name=created_obj.name,
            email=created_obj.email,
            password=created_obj.password,
            registration_date=created_obj.registration_date,
            active=created_obj.active
        )

    def find_by_email(self, email: str):
        try:
            obj = UserModel.objects.get(email=email)
            return User(
                id=obj.id,
                name=obj.name,
                email=obj.email,
                password=obj.password,
                registration_date=obj.registration_date,
                active=obj.active,
                _is_hashed=True
            )
        except UserModel.DoesNotExist:
            return None