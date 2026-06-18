from datetime import date
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Enum as SQLEnum, Date, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.config import settings
from src.modules.shared.application.enums import Role
from src.modules.shared.infrastructure.models import BaseModel
from src.modules.user.application.enums import Gender
from src.modules.user.domain.value_objects import Phone, Email, Name
from src.modules.user.domain.entities import User

if TYPE_CHECKING:
    from src.modules.authentication.infrastructure.models import SessionModel


class UserModel(BaseModel):
    __tablename__ = f"{settings.APPLICATION_TABLE_PREFIX}_users"
    __table_args__ = (
        UniqueConstraint("email", "is_active", name="uq_users_email_is_active"),
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        name="first_name",
        comment="First name of the user",
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        name="last_name",
        comment="Last name of the user",
        nullable=False,
    )

    preferred_name: Mapped[str] = mapped_column(
        String(100),
        name="preferred_name",
        comment="Preferred name of the user",
        nullable=False,
    )

    gender: Mapped[Gender] = mapped_column(
        SQLEnum(Gender, name="gender_enum"),
        name="gender",
        comment="Gender of the user",
        nullable=False,
    )

    birthdate: Mapped[date] = mapped_column(
        Date,
        name="birthdate",
        comment="Birthdate of the user",
        nullable=False,
    )

    email: Mapped[Email] = mapped_column(
        String(255),
        name="email",
        comment="Email address of the user",
        nullable=False,
    )

    phone: Mapped[Optional[Phone]] = mapped_column(
        String(18),
        name="phone",
        comment="Phone number of the user",
        nullable=True,
        default=None,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        name="hashed_password",
        comment="Hashed password of the user",
        nullable=False,
    )

    role: Mapped[Role] = mapped_column(
        SQLEnum(Role, name="role_enum"),
        name="role",
        comment="Role of the user",
        nullable=False,
        default=Role.CANDIDATE,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        name="is_active",
        comment="User active status",
        nullable=False,
        default=True,
    )

    sessions: Mapped[list["SessionModel"]] = relationship(
        "SessionModel",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @classmethod
    def from_entity(cls, user: User) -> "UserModel":
        return cls(
            id=user.id,
            first_name=user.name.first_name,
            last_name=user.name.last_name,
            preferred_name=user.name.preferred_name,
            gender=user.gender,
            birthdate=user.birthdate,
            email=str(user.email),
            phone=str(user.phone) if user.phone else None,
            hashed_password=user.hashed_password,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def to_entity(self) -> User:
        return User(
            id=self.id,
            name=Name(
                first_name=self.first_name,
                last_name=self.last_name,
                preferred_name=self.preferred_name,
            ),
            gender=self.gender,
            birthdate=self.birthdate,
            email=Email(self.email.__str__()),
            phone=Phone(self.phone.__str__()) if self.phone else None,
            hashed_password=self.hashed_password,
            role=self.role,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
