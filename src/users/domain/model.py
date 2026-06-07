# src/users/domain/model.py
import re
from enum import Enum
from typing import List, Callable

from src.users.domain.events import (
    DomainEvent,
    UserRegistered,
    UserSuspended,
    UserApproved,
    PasswordChanged,
)
from src.users.domain.exceptions import (
    AccountSuspendedError,
    InsufficientPermissionError,
    InvalidEmailError,
    WeakPasswordError,
)

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LENGTH = 8


class UserRole(str, Enum):
    admin = "admin"
    employer = "employer"
    candidate = "candidate"


class User:
    def __init__(
        self,
        email: str,
        hashed_password: str,
        role: UserRole,
        is_activated: bool = True,
    ):
        self.email = email
        self.hashed_password = hashed_password
        self.role = role
        self.is_activated = is_activated
        self.events: List[DomainEvent] = []

    @property
    def is_superuser(self) -> bool:
        return self.role == UserRole.admin

    def _guard_suspended(self) -> None:
        """Raise if the account is suspended before allowing any interaction."""
        if not self.is_activated:
            raise AccountSuspendedError(email=self.email)

    def _guard_admin(self, action: str) -> None:
        """Raise if the actor is not an admin."""
        if not self.is_superuser:
            raise InsufficientPermissionError(action=action)

    @classmethod
    def register(
        cls,
        email: str,
        plain_password: str,
        role: UserRole,
        password_hasher: Callable[[str], str],
    ) -> "User":
        """Factory method — create and return a new User, emitting UserRegistered.

        Employers start as inactive (PENDING) and require admin approval.
        Candidates are activated immediately upon registration.
        """
        if not _EMAIL_REGEX.match(email):
            raise InvalidEmailError()
        if len(plain_password) < _MIN_PASSWORD_LENGTH:
            raise WeakPasswordError()

        hashed_password = password_hasher(plain_password)
        is_activated = role != UserRole.employer

        user = cls(
            email=email,
            hashed_password=hashed_password,
            role=role,
            is_activated=is_activated,
        )
        user.events.append(UserRegistered(email=email, role=role.value))
        return user

    def verify_password(
        self, plain_password: str, verifier_fn: Callable[[str, str], bool]
    ) -> bool:
        """Verify a plain-text password against the stored hash.

        Delegates the hashing strategy to the caller (Dependency Inversion).
        Blocked if the account is suspended.
        """
        self._guard_suspended()
        return verifier_fn(plain_password, self.hashed_password)

    def change_password(
        self, plain_new_password: str, password_hasher: Callable[[str], str]
    ) -> None:
        """Replace the current password hash and emit PasswordChanged.

        Blocked if the account is suspended.
        """
        self._guard_suspended()
        self.hashed_password = password_hasher(plain_new_password)
        self.events.append(PasswordChanged(email=self.email))

    def suspend(self, target_user: "User") -> None:
        """Admin action — deactivate a user account and emit UserSuspended."""
        self._guard_admin("suspend users")
        target_user.is_activated = False
        target_user.events.append(
            UserSuspended(email=target_user.email, role=target_user.role.value)
        )

    def approve(self, target_user: "User") -> None:
        """Admin action — activate a pending employer account and emit UserApproved."""
        self._guard_admin("approve users")
        target_user.is_activated = True
        target_user.events.append(
            UserApproved(email=target_user.email, role=target_user.role.value)
        )
