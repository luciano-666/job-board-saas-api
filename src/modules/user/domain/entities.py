from dataclasses import dataclass, field
from typing import Union
from datetime import date
from uuid import UUID, uuid4

from src.modules.shared.application.enums import Role
from src.modules.shared.domain.entities import DomainError
from src.modules.user.domain.exceptions import (
    AccountSuspendedError,
    InsufficientPermissionError,
)
from src.modules.user.application.enums import Gender
from src.modules.user.domain.value_objects import Name, Email, Phone


@dataclass(kw_only=True, slots=True)
class User:
    name: Name | None = field(default=None, repr=True, compare=False)
    gender: Gender | None = field(default=None, repr=False, compare=False)
    birthdate: date | None = field(default=None, repr=True, compare=False)
    email: Union[Email, str] = field(repr=True, compare=True)
    phone: Union[Phone, str] | None = field(default=None, repr=False, compare=False)

    # Application generated fields
    id: UUID = field(default_factory=uuid4, repr=True, compare=True)
    is_active: bool = field(init=False, default=True, repr=False, compare=False)
    hashed_password: str | None = field(default=None, repr=False, compare=False)
    role: Role = field(default=Role.CANDIDATE, repr=False, compare=False)

    @property
    def is_superuser(self) -> bool:
        return self.role == Role.ADMIN

    def __post_init__(self):
        self._normalize()
        self._validate()

    def _normalize(self):
        if isinstance(self.email, str):
            self.email = Email(email=self.email)
        if isinstance(self.phone, str):
            self.phone = Phone(phone=self.phone)

    def _validate(self) -> None:
        if self.birthdate is None:
            return

        today = date.today()
        age = (
            today.year
            - self.birthdate.year
            - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))
        )
        if age < 18:
            raise DomainError("Users must be at least 18 years old.")

    def _guard_suspended(self) -> None:
        """Raise if the account is suspended before allowing any interaction."""
        if not self.is_active:
            raise AccountSuspendedError(email=str(self.email))

    def _guard_admin(self, action: str) -> None:
        """Raise if the actor is not an admin."""
        if not self.is_superuser:
            raise InsufficientPermissionError(action=action)

    def suspend(self, target_user: "User") -> None:
        """Admin action — deactivate a user account and emit UserSuspended."""
        self._guard_admin("suspend users")
        target_user.is_active = False

    def approve(self, target_user: "User") -> None:
        """Admin action — activate a pending employer account and emit UserApproved."""
        self._guard_admin("approve users")
        target_user.is_active = True
