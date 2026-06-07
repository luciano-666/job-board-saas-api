class UserDomainError(Exception):
    """Base exception for the users bounded context."""


class AccountSuspendedError(UserDomainError, PermissionError):
    """Account has been suspended — all interactions are blocked."""

    def __init__(self, email: str | None = None) -> None:
        self.email = email
        super().__init__("This account has been suspended")


class InsufficientPermissionError(UserDomainError, PermissionError):
    """The actor does not have permission to perform this action."""

    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(f"Only admin can {action}")


class InvalidEmailError(UserDomainError, ValueError):
    """Email address does not match the required format."""

    def __init__(self) -> None:
        super().__init__("Invalid email address")


class WeakPasswordError(UserDomainError, ValueError):
    """Password does not meet the minimum length requirement."""

    def __init__(self) -> None:
        super().__init__("Password is too short")
