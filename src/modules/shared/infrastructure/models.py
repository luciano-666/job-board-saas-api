from datetime import datetime, UTC
from uuid import UUID

from sqlalchemy import Boolean, func, DateTime, UUID as SQUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[UUID] = mapped_column(
        SQUID(as_uuid=True),
        name="id",
        comment="Unique identifier of the record",
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="created_at",
        comment="Timestamp when the record was created",
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="updated_at",
        comment="Timestamp when the record was last updated",
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=func.now(),
    )
