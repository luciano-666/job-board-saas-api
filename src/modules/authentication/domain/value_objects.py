from dataclasses import dataclass
from uuid import UUID
import secrets

from src.modules.shared.domain.entities import DomainError


@dataclass(frozen=True, slots=True, kw_only=True)
class BaseClaims:
    iss: str
    sub: UUID
    aud: str
    iat: int
    nbf: int
    exp: int
    jti: UUID
    grant_id: str
    scope: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "iss", self.iss.strip())
        object.__setattr__(self, "aud", self.aud.strip())
        object.__setattr__(self, "scope", " ".join(self.scope.lower().split()))

        self._validate()

    def _validate(self) -> None:
        if not self.iss:
            raise DomainError("Claims issuer (iss) is required.")

        if not self.sub:
            raise DomainError("Claims subject (sub) is required.")

        if not self.aud:
            raise DomainError("Claims audience (aud) is required.")

        if not isinstance(self.iat, int) or self.iat <= 0:
            raise DomainError(
                "Claims issued at (iat) must be a positive integer Unix timestamp."
            )

        if not isinstance(self.nbf, int) or self.nbf <= 0:
            raise DomainError(
                "Claims not before (nbf) must be a positive integer Unix timestamp."
            )

        if self.nbf < self.iat:
            raise DomainError(
                "Claims not before (nbf) cannot be earlier than issued at (iat)."
            )

        if not isinstance(self.exp, int) or self.exp <= 0:
            raise DomainError(
                "Claims expiration (exp) must be a positive integer Unix timestamp."
            )

        if self.exp <= self.iat:
            raise DomainError("Claims expiration (exp) must be after issued at (iat).")

        if not self.jti:
            raise DomainError("Claims JWT ID (jti) is required.")

        if not self.grant_id:
            raise DomainError("Claims grant_id is required.")

        if not self.scope:
            raise DomainError("Claims scope is required.")

    def to_dict(self) -> dict:
        return {
            "iss": self.iss,
            "sub": str(self.sub),
            "aud": self.aud,
            "iat": self.iat,
            "nbf": self.nbf,
            "exp": self.exp,
            "jti": str(self.jti),
            "grant_id": self.grant_id,
            "scope": self.scope,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class Claims(BaseClaims):
    @classmethod
    def from_dict(cls, data: dict) -> "Claims":
        return cls(
            iss=data["iss"],
            sub=UUID(data["sub"]),
            aud=data["aud"],
            iat=data["iat"],
            nbf=data["nbf"],
            exp=data["exp"],
            jti=UUID(data["jti"]),
            grant_id=data["grant_id"],
            scope=data["scope"],
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class RefreshClaims(BaseClaims):
    client_id: str

    def __post_init__(self) -> None:
        super().__post_init__()

        object.__setattr__(
            self,
            "client_id",
            self.client_id.strip().lower(),
        )

        if not self.client_id:
            raise DomainError("Refresh claims client_id is required.")

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["client_id"] = self.client_id
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "RefreshClaims":
        return cls(
            iss=data["iss"],
            sub=UUID(data["sub"]),
            aud=data["aud"],
            iat=data["iat"],
            nbf=data["nbf"],
            exp=data["exp"],
            jti=UUID(data["jti"]),
            client_id=data["client_id"],
            grant_id=data["grant_id"],
            scope=data["scope"],
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Credentials:
    """Raw login credentials, decoupled from the User module's domain model."""

    email: str
    password: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PasswordResetToken:
    """Raw reset token issued to the user (sent via email, never persisted as-is)."""

    value: str

    @classmethod
    def generate(cls) -> "PasswordResetToken":
        return cls(value=secrets.token_urlsafe(32))
