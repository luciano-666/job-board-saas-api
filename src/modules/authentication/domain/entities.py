from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import UUID

from src.modules.authentication.application.enums import TokenType
from src.modules.authentication.domain.value_objects import Claims, RefreshClaims
from src.modules.shared.application.enums import Role
from src.modules.user.domain.entities import User


# ---------------------------------------------------------------------------
# AccessToken
# ---------------------------------------------------------------------------


@dataclass(kw_only=True, slots=True)
class AccessToken:
    """Represents a JWT access token and its metadata.

    Lifecycle:
      - Created with only expiry info (before token generation).
      - After generate_tokens(): token and hashed_jti are populated.
      - After DB persist: id is populated.
    """

    expires_at: datetime
    permission: Role = field(default=Role.CANDIDATE)

    # Populated after token generation
    token: str | None = field(default=None, repr=False)
    hashed_jti: str | None = field(default=None, repr=False)
    previous_hashed_jti: str | None = field(default=None, repr=False)
    claims: Claims | None = field(default=None, repr=False)

    # Populated after DB persist
    id: UUID | None = field(default=None, repr=True)
    created_at: datetime | None = field(default=None, repr=False)

    # Revocation state
    revoked: bool = field(default=False, repr=False)
    revoked_at: datetime | None = field(default=None, repr=False)

    def revoke(self) -> None:
        self.revoked = True
        self.revoked_at = datetime.now(UTC)

    def activate(self) -> None:
        self.revoked = False
        self.revoked_at = None

    def stamp_created_at(self) -> None:
        self.created_at = datetime.now(UTC)

    def rotate_jti(self) -> None:
        """Save current hashed_jti as previous before issuing a new one."""
        self.previous_hashed_jti = self.hashed_jti

    def set_claims(
        self,
        iss: str,
        sub: UUID,
        aud: str,
        jti: UUID,
        grant_id: str,
        scope: str,
    ) -> None:
        if self.created_at is None:
            raise ValueError("created_at must be set before generating claims.")
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


# ---------------------------------------------------------------------------
# RefreshToken
# ---------------------------------------------------------------------------


@dataclass(kw_only=True, slots=True)
class RefreshToken:
    """Represents a refresh token paired with one AccessToken.

    Lifecycle:
      - Created with only expiry info.
      - After token generation: token and hashed_jti are populated.
      - After DB persist: id is populated.
    """

    expires_at: datetime
    access_token: AccessToken

    # Populated after token generation
    token: str | None = field(default=None, repr=False)
    hashed_jti: str | None = field(default=None, repr=False)
    previous_hashed_jti: str | None = field(default=None, repr=False)
    refresh_claims: RefreshClaims | None = field(default=None, repr=False)

    # Populated after DB persist
    id: UUID | None = field(default=None, repr=True)
    created_at: datetime | None = field(default=None, repr=False)
    updated_at: datetime | None = field(default=None, repr=False)

    # Revocation state
    revoked: bool = field(default=False, repr=False)
    revoked_at: datetime | None = field(default=None, repr=False)

    def revoke(self) -> None:
        self.revoked = True
        self.revoked_at = datetime.now(UTC)

    def activate(self) -> None:
        self.revoked = False
        self.revoked_at = None

    def stamp_created_at(self) -> None:
        self.created_at = datetime.now(UTC)

    def stamp_updated_at(self) -> None:
        self.updated_at = datetime.now(UTC)

    def rotate_jti(self) -> None:
        """Save current hashed_jti as previous before issuing a new one."""
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
            raise ValueError("updated_at must be set before generating claims.")
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


# ---------------------------------------------------------------------------
# SessionRequest  — input from the HTTP layer, before any DB interaction
# ---------------------------------------------------------------------------


@dataclass(kw_only=True, slots=True)
class SessionRequest:
    """Captures request context collected at the presentation layer.

    Passed into AuthenticationUseCases.login().
    The user field must already hold verified credentials (email + raw password)
    so the use case can authenticate against the DB record.
    """

    user: User
    ip_address: str
    user_agent: str
    device: str
    location: str | None = field(default=None)
    accept_language: str | None = field(default=None)
    accept_encoding: str | None = field(default=None)
    origin: str | None = field(default=None)
    referer: str | None = field(default=None)

    def __post_init__(self) -> None:
        self._normalize()

    def _normalize(self) -> None:
        self.ip_address = self.ip_address.lower().strip()
        self.user_agent = self.user_agent.lower().strip()
        self.device = self.device.lower().strip()
        if self.accept_language:
            self.accept_language = self.accept_language.lower().strip()
        if self.accept_encoding:
            self.accept_encoding = self.accept_encoding.lower().strip()
        if self.origin:
            self.origin = self.origin.lower().strip()
        if self.referer:
            self.referer = self.referer.lower().strip()
        if self.location:
            self.location = self.location.lower().strip()


# ---------------------------------------------------------------------------
# Session  — a fully persisted session returned from the repository
# ---------------------------------------------------------------------------


@dataclass(kw_only=True, slots=True)
class Session:
    """A persisted authentication session with associated tokens.

    Returned by the repository after create/get operations.
    All required fields are non-optional: the repository guarantees
    they exist before constructing this object.
    """

    id: UUID
    user: User
    refresh_token: RefreshToken
    ip_address: str
    user_agent: str
    device: str
    created_at: datetime
    last_updated_at: datetime
    token_type: TokenType = field(default=TokenType.BEARER)
    blacklisted: bool = field(default=False)

    # Optional request metadata stored for audit / analytics
    location: str | None = field(default=None)
    accept_language: str | None = field(default=None)
    accept_encoding: str | None = field(default=None)
    origin: str | None = field(default=None)
    referer: str | None = field(default=None)

    def touch(self) -> None:
        """Update last_updated_at to now."""
        self.last_updated_at = datetime.now(UTC)


@dataclass(kw_only=True, slots=True)
class SessionLookup:
    """Minimal identifying info extracted from JWT claims, used to query
    a persisted Session by access token or refresh token.

    Unlike Session, this does not represent a persisted record — it only
    carries the fields the repository needs to run its lookup query.
    """

    user_id: UUID
    user_agent: str
    hashed_jti: str
    device: str | None = field(default=None)

    def __post_init__(self) -> None:
        self._normalize()

    def _normalize(self) -> None:
        self.user_agent = self.user_agent.lower().strip()
        if self.device:
            self.device = self.device.lower().strip()

    @classmethod
    def from_access_session(cls, session: Session) -> SessionLookup:
        hashed_jti = session.refresh_token.access_token.hashed_jti
        if hashed_jti is None:
            raise ValueError(
                "Access token hashed_jti is None — token has not been hashed yet."
            )

        return cls(
            user_id=session.user.id,
            user_agent=session.user_agent,
            hashed_jti=hashed_jti,
            device=session.device,
        )

    @classmethod
    def from_refresh_session(cls, session: Session) -> SessionLookup:
        hashed_jti = session.refresh_token.hashed_jti
        if hashed_jti is None:
            raise ValueError(
                "Refresh token hashed_jti is None — token has not been hashed yet."
            )

        return cls(
            user_id=session.user.id,
            user_agent=session.user_agent,
            hashed_jti=hashed_jti,
            device=session.device,
        )
