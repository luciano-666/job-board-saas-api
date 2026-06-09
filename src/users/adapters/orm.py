from sqlalchemy import Column, Table, Boolean, String, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import registry

from src.users.domain.model import User, UserRole

mapper_registry = registry()

metadata = mapper_registry.metadata

users_table = Table(
    "users",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("hashed_password", String(255), nullable=False),
    Column("role", SQLEnum(UserRole), nullable=False),
    Column("is_activated", Boolean, default=True),
)


mapper_registry.map_imperatively(User, users_table)
