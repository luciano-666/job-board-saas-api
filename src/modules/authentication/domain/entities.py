from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import UUID

from src.modules.authentication.application.enums import TokenType
from src.modules.authentication.domain.value_objects import Claims, RefreshClaims
from src.modules.shared.application.enums import Role
from src.modules.shared.domain.entities import DomainError
from src.modules.user.domain.entities import User


@dataclass(kw_only=True, slots=True)
class Session:
    ip_address: str | None = field(default=None, repr=True, compare=True)
    user_agent: str | None = field(default=None, repr=True, compare=True)
    device: str | None = field(default=None, repr=True, compare=True)
    location: str | None = field(default=None, repr=True, compare=False)
    accept_language: str | None = field(default=None, repr=True, compare=False)
    accept_encoding: str | None = field(default=None, repr=True, compare=False)
    origin: str | None = field(default=None, repr=True, compare=False)
    referer: str | None = field(default=None, repr=True, compare=False)

    # Application generated fields
    id: UUID | None = field(default=None, repr=True, compare=True)
    created_at: datetime | None = field(default=None, repr=False, compare=True)
    last_updated_at: datetime | None = field(default=None, repr=False, compare=False)
    blacklisted: bool = field(init=False, default=False, repr=False, compare=False)
    token_type: TokenType = field(
        init=False, default=TokenType.BEARER, repr=False, compare=False
    )

    # Foreign entities
    user: User | None = field(default=None, compare=True, repr=True)
    refresh_token: RefreshToken | None = field(default=None, compare=True, repr=True)

    def __post_init__(self):
        self._normalize()

    def _normalize(self):
        self.ip_address = self.ip_address.lower().strip() if self.ip_address else None
        self.user_agent = self.user_agent.lower().strip() if self.user_agent else None
        self.accept_language = (
            self.accept_language.lower().strip() if self.accept_language else None
        )
        self.accept_encoding = (
            self.accept_encoding.lower().strip() if self.accept_encoding else None
        )
        self.origin = self.origin.lower().strip() if self.origin else None
        self.referer = self.referer.lower().strip() if self.referer else None
        self.location = self.location.lower().strip() if self.location else None

    def update_last_updated_at(self):
        self.last_updated_at = datetime.now(UTC)


@dataclass(kw_only=True)
class RefreshToken:
    token: str | None = field(default=None, repr=False, compare=False)
    hashed_jti: str | None = field(default=None, repr=False, compare=True)
    previous_hashed_jti: str | None = field(default=None, repr=False, compare=True)

    # Application generated fields
    replaced_by_token: UUID | None = field(default=None, repr=False, compare=False)
    id: UUID | None = field(default=None, repr=True, compare=True)
    created_at: datetime | None = field(default=None, repr=False, compare=True)
    updated_at: datetime | None = field(default=None, repr=False, compare=False)
    expires_at: datetime | None = field(default=None, repr=False, compare=False)
    revoked: bool = field(init=False, default=False, repr=False, compare=False)
    revoked_at: datetime | None = field(
        init=False, default=None, repr=False, compare=False
    )
    refresh_claims: RefreshClaims | None = field(
        default=None, repr=False, compare=False
    )

    # Foreign entities
    access_token: AccessToken | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if self.revoked:
            raise DomainError("Refresh token has been revoked.")

    def revoke(self):
        self.revoked = True
        self.revoked_at = datetime.now(UTC)

    def activate(self):
        self.revoked = False
        self.revoked_at = None

    def generate_created_at(self):
        self.created_at = datetime.now(UTC)

    def generate_updated_at(self):
        self.updated_at = datetime.now(UTC)

    def update_previous_hashed_jti(self):
        self.previous_hashed_jti = self.hashed_jti

    def set_claims(
        self,
        iss: str,
        sub: UUID,
        aud: str,
        jti: UUID,
        client_id: str,
        grant_id: str,
        scope: str,
    ) -> None:
        if self.updated_at is None:
            raise DomainError("updated_at is required before generating claims.")

        if self.expires_at is None:
            raise DomainError("expires_at is required before generating claims.")

        self.refresh_claims = RefreshClaims(
            iss=iss,
            sub=sub,
            aud=aud,
            iat=int(self.updated_at.timestamp()),
            nbf=int(self.updated_at.timestamp()),
            exp=int(self.expires_at.timestamp()),
            jti=jti,
            client_id=client_id,
            grant_id=grant_id,
            scope=scope,
        )


@dataclass(kw_only=True)
class AccessToken:
    token: str | None = field(default=None, repr=False, compare=False)
    hashed_jti: str | None = field(default=None, repr=False, compare=True)
    previous_hashed_jti: str | None = field(default=None, repr=False, compare=True)
    permission: Role = field(default=Role.CANDIDATE, repr=False, compare=False)

    # Application generated fields
    id: UUID | None = field(default=None, repr=True, compare=True)
    created_at: datetime | None = field(default=None, repr=False, compare=True)
    expires_at: datetime | None = field(default=None, repr=False, compare=False)
    claims: Claims | None = field(default=None, repr=False, compare=False)
    revoked: bool = field(init=False, default=False, repr=False, compare=False)
    revoked_at: datetime | None = field(
        init=False, default=None, repr=False, compare=False
    )

    def revoke(self):
        self.revoked = True
        self.revoked_at = datetime.now(UTC)

    def activate(self):
        self.revoked = False
        self.revoked_at = None

    def generate_created_at(self):
        self.created_at = datetime.now(UTC)

    def update_previous_hashed_jti(self):
        self.previous_hashed_jti = self.hashed_jti

    def set_claims(
        self, iss: str, sub: UUID, aud: str, jti: UUID, grant_id: str, scope: str
    ) -> None:
        if self.created_at is None:
            raise DomainError("updated_at is required before generating claims.")

        if self.expires_at is None:
            raise DomainError("expires_at is required before generating claims.")

        self.claims = Claims(
            iss=iss,
            sub=sub,
            aud=aud,
            iat=int(self.created_at.timestamp()),
            nbf=int(self.created_at.timestamp()),
            exp=int(self.expires_at.timestamp()),
            jti=jti,
            grant_id=grant_id,
            scope=scope,
        )
