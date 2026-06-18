from src.modules.user.domain.entities import User
from src.modules.user.domain.value_objects import Name, Email, Phone
from src.modules.user.infrastructure.models import UserModel


def to_model(entity: User) -> UserModel:
    return UserModel(
        id=entity.id,
        first_name=entity.name.first_name,
        last_name=entity.name.last_name,
        preferred_name=entity.name.preferred_name,
        gender=entity.gender,
        birthdate=entity.birthdate,
        email=str(entity.email),
        phone=str(entity.phone) if entity.phone else None,
        hashed_password=entity.hashed_password,
        role=entity.role,
        is_active=entity.is_active,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        name=Name(
            first_name=model.first_name,
            last_name=model.last_name,
            preferred_name=model.preferred_name,
        ),
        gender=model.gender,
        birthdate=model.birthdate,
        email=Email(model.email.__str__()),
        phone=Phone(model.phone.__str__()) if model.phone else None,
        hashed_password=model.hashed_password,
        role=model.role,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
