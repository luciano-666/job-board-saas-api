from datetime import datetime, UTC
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    String,
    Text,
    DateTime,
    func,
    UniqueConstraint,
    ForeignKey,
    UUID as SQUID,
    Index,
    Boolean,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.config import settings
from src.modules.shared.application.enums import Role
from src.modules.shared.infrastructure.models import Base

if TYPE_CHECKING:
    from src.modules.authentication.domain.entities import (
        Session,
        AccessToken,
        RefreshToken,
    )
    from src.modules.user.infrastructure.models import UserModel


class AccessTokenModel(Base):
    __tablename__ = f"{settings.APPLICATION_TABLE_PREFIX}_access_tokens"
    __table_args__ = (
        UniqueConstraint("refresh_id", name="uq_access_tokens_refresh_id"),
        Index("ix_access_tokens_hashed_jti_revoked", "hashed_jti", "revoked"),
    )
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[UUID] = mapped_column(
        SQUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        name="id",
        comment="Unique identifier of the access token",
    )
    refresh_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            f"{settings.APPLICATION_TABLE_PREFIX}_refresh_tokens.id", ondelete="CASCADE"
        ),
        name="refresh_id",
        comment="Refresh token associated with this access token",
        nullable=False,
    )
    hashed_jti: Mapped[str] = mapped_column(
        Text,
        name="hashed_jti",
        comment="Hashed JTI (JWT ID) value",
        nullable=False,
        unique=True,
    )
    previous_hashed_jti: Mapped[Optional[str]] = mapped_column(
        Text,
        name="previous_hashed_jti",
        comment="Hashed JTI (JWT ID) value of the previous access token",
        nullable=True,
        default=None,
        unique=True,
    )
    permission: Mapped[Role] = mapped_column(
        SQLEnum(Role, name="role_enum"),
        name="permission",
        comment="Permission level associated with the access token",
        nullable=False,
        default=Role.CANDIDATE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="created_at",
        comment="Timestamp when the access token was created",
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="expires_at",
        comment="Expiration timestamp of the access token",
        nullable=False,
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        name="revoked",
        comment="Indicates whether the access token was revoked",
        nullable=False,
        default=False,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        name="revoked_at",
        comment="Timestamp when the access token was revoked",
        nullable=True,
        default=None,
    )
    refresh_token: Mapped["RefreshTokenModel"] = relationship(
        back_populates="access_token",
        uselist=False,
    )

    @classmethod
    def from_entity(cls, access: "AccessToken") -> "AccessTokenModel":
        return cls(
            id=access.id,
            hashed_jti=access.hashed_jti,
            previous_hashed_jti=access.previous_hashed_jti,
            created_at=access.created_at,
            expires_at=access.expires_at,
            permission=access.permission,
            revoked=access.revoked if access.revoked is not None else False,
            revoked_at=access.revoked_at,
        )

    def to_entity(self) -> "AccessToken":
        from src.modules.authentication.domain.entities import AccessToken

        entity = AccessToken(
            expires_at=self.expires_at,
            permission=self.permission,
            hashed_jti=self.hashed_jti,
            previous_hashed_jti=self.previous_hashed_jti,
            id=self.id,
            created_at=self.created_at,
        )
        entity.revoked = self.revoked
        entity.revoked_at = self.revoked_at
        return entity


class RefreshTokenModel(Base):
    __tablename__ = f"{settings.APPLICATION_TABLE_PREFIX}_refresh_tokens"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_refresh_tokens_session_id"),
        Index("ix_refresh_tokens_hashed_jti_revoked", "hashed_jti", "revoked"),
    )
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[UUID] = mapped_column(
        SQUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        name="id",
        comment="Unique identifier of the refresh token",
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            f"{settings.APPLICATION_TABLE_PREFIX}_sessions.id", ondelete="CASCADE"
        ),
        name="session_id",
        comment="Session associated with this refresh token",
        nullable=False,
    )
    hashed_jti: Mapped[str] = mapped_column(
        Text,
        name="hashed_jti",
        comment="Hashed JTI (JWT ID) value",
        nullable=False,
        unique=True,
    )
    previous_hashed_jti: Mapped[Optional[str]] = mapped_column(
        Text,
        name="previous_hashed_jti",
        comment="Hashed JTI (JWT ID) value of the previous refresh token",
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="created_at",
        comment="Timestamp when the refresh token was created",
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="updated_at",
        comment="Timestamp when the record was last updated",
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="expires_at",
        comment="Expiration timestamp of the refresh token",
        nullable=False,
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        name="revoked",
        comment="Indicates whether the refresh token was revoked",
        nullable=False,
        default=False,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        name="revoked_at",
        comment="Timestamp when the refresh token was revoked",
        nullable=True,
        default=None,
    )
    session: Mapped["SessionModel"] = relationship(
        back_populates="refresh_token",
        uselist=False,
    )
    access_token: Mapped["AccessTokenModel"] = relationship(
        back_populates="refresh_token",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @classmethod
    def from_entity(cls, refresh: "RefreshToken") -> "RefreshTokenModel":
        model = cls(
            id=refresh.id,
            hashed_jti=refresh.hashed_jti,
            previous_hashed_jti=refresh.previous_hashed_jti,
            created_at=refresh.created_at,
            updated_at=refresh.updated_at,
            expires_at=refresh.expires_at,
            revoked=refresh.revoked if refresh.revoked is not None else False,
            revoked_at=refresh.revoked_at,
        )
        if refresh.access_token:
            model.access_token = AccessTokenModel.from_entity(refresh.access_token)
        return model

    def to_entity(self) -> "RefreshToken":
        from src.modules.authentication.domain.entities import RefreshToken

        if self.access_token is None:
            raise ValueError(
                "RefreshTokenModel.access_token must be loaded before calling to_entity()."
            )
        entity = RefreshToken(
            expires_at=self.expires_at,
            access_token=self.access_token.to_entity(),
            hashed_jti=self.hashed_jti,
            previous_hashed_jti=self.previous_hashed_jti,
            id=self.id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
        entity.revoked = self.revoked
        entity.revoked_at = self.revoked_at
        return entity


class SessionModel(Base):
    __tablename__ = f"{settings.APPLICATION_TABLE_PREFIX}_sessions"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "user_agent",
            "device",
            name="uq_sessions_user_id_user_agent_device",
        ),
        Index(
            "ix_sessions_user_id_user_agent_device", "user_id", "user_agent", "device"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        SQUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        name="id",
        comment="Unique identifier of the session",
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{settings.APPLICATION_TABLE_PREFIX}_users.id", ondelete="CASCADE"),
        name="user_id",
        comment="Identifier of the user who owns the session",
        nullable=False,
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        name="ip_address",
        comment="IP address used when the session was created",
        nullable=False,
    )
    device: Mapped[str] = mapped_column(
        String(255),
        name="device",
        comment="Human readable device name",
        nullable=False,
    )
    user_agent: Mapped[str] = mapped_column(
        Text,
        name="user_agent",
        comment="User agent string of the client",
        nullable=False,
    )
    accept_language: Mapped[Optional[str]] = mapped_column(
        String(255),
        name="accept_language",
        comment="Accept-Language header value of the client",
        nullable=True,
        default=None,
    )
    accept_encoding: Mapped[Optional[str]] = mapped_column(
        String(255),
        name="accept-encoding",
        comment="Accept-Encoding header value of the client",
        nullable=True,
        default=None,
    )
    origin: Mapped[str] = mapped_column(
        String(255),
        name="origin",
        comment="Origin header value of the client",
        nullable=False,
    )
    referrer: Mapped[Optional[str]] = mapped_column(
        String(255),
        name="referrer",
        comment="Referrer header value of the client",
        nullable=False,
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(255),
        name="location",
        comment="Approximate geographic location of the client",
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="created_at",
        comment="Timestamp when the session was created",
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="last_update_at",
        comment="Last time the session was updated",
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    blacklisted: Mapped[bool] = mapped_column(
        Boolean,
        name="blacklisted",
        comment="Indicates whether the session is blacklisted",
        nullable=False,
        default=False,
    )
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="sessions")
    refresh_token: Mapped["RefreshTokenModel"] = relationship(
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @classmethod
    def from_entity(cls, session: "Session") -> "SessionModel":
        model = cls(
            id=session.id,
            user_id=session.user.id,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            device=session.device,
            accept_language=session.accept_language,
            accept_encoding=session.accept_encoding,
            origin=session.origin,
            referrer=session.referer,
            location=session.location,
            created_at=session.created_at,
            last_updated_at=session.last_updated_at,
            blacklisted=session.blacklisted,
        )
        if session.refresh_token:
            model.refresh_token = RefreshTokenModel.from_entity(session.refresh_token)
        return model

    def to_entity(self) -> "Session":
        from src.modules.authentication.domain.entities import Session

        if self.user is None:
            raise ValueError(
                "SessionModel.user must be loaded before calling to_entity()."
            )
        if self.refresh_token is None:
            raise ValueError(
                "SessionModel.refresh_token must be loaded before calling to_entity()."
            )

        entity = Session(
            id=self.id,
            user=self.user.to_entity(),
            refresh_token=self.refresh_token.to_entity(),
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            device=self.device,
            created_at=self.created_at,
            last_updated_at=self.last_updated_at,
            location=self.location,
            accept_language=self.accept_language,
            accept_encoding=self.accept_encoding,
            origin=self.origin,
            referer=self.referrer,
        )
        entity.blacklisted = self.blacklisted
        return entity
