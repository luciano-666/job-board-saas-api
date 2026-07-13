from dataclasses import dataclass, field
from datetime import date, datetime, UTC
from uuid import UUID, uuid4

from src.modules.shared.application.enums import Role
from src.modules.shared.domain.entities import DomainError
from src.modules.user.application.enums import Gender
from src.modules.user.domain.value_objects import Name, Email, Phone


@dataclass(kw_only=True, slots=True)
class User:
    name: Name = field(
        default_factory=lambda: Name(first_name="", last_name="", preferred_name=None),
        repr=True,
        compare=False,
    )
    gender: Gender | None = field(default=None, repr=False, compare=False)
    birthdate: date | None = field(default=None, repr=True, compare=False)
    email: Email | str = field(repr=True, compare=True)
    phone: Phone | str | None = field(default=None, repr=False, compare=False)
    password: str | None = field(default=None, repr=False, compare=False)

    # Application generated fields
    id: UUID = field(default_factory=uuid4, repr=True, compare=True)
    created_at: datetime = field(default=datetime.now(UTC), repr=False, compare=True)
    updated_at: datetime = field(default=datetime.now(UTC), repr=False, compare=False)
    is_active: bool = field(default=True, repr=False, compare=False)
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

    def suspend(self) -> None:
        if not self.is_active:
            raise DomainError("User is already suspended.")
        self.is_active = False

    def activate(self) -> None:
        if self.is_active:
            raise DomainError("User is already active.")
        self.is_active = True
