"""Application-layer DTOs for the applications module: cursor pagination,
filters, and the presentation-ready view returned by list use cases."""

from __future__ import annotations
from dataclasses import dataclass, field

import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from src.modules.applications.application.enums import ApplicationStatus
from src.modules.applications.domain.entities import Application


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationCursor:
    """Opaque pagination cursor encoding (created_at, application_id).

    Same rationale as JobCursor: sorting is created_at DESC, id DESC as
    tiebreaker — no OFFSET, per spec constraint on cursor-based pagination.
    """

    created_at: datetime
    application_id: UUID

    def encode(self) -> str:
        payload = {
            "created_at": self.created_at.isoformat(),
            "application_id": str(self.application_id),
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    @classmethod
    def decode(cls, cursor: str) -> "ApplicationCursor":
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
            payload = json.loads(raw)
        except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError("Invalid pagination cursor.") from e

        if (
            not isinstance(payload, dict)
            or "created_at" not in payload
            or "application_id" not in payload
        ):
            raise ValueError("Malformed pagination cursor payload.")

        try:
            return cls(
                created_at=datetime.fromisoformat(payload["created_at"]),
                application_id=UUID(payload["application_id"]),
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError("Malformed pagination cursor payload.") from e


@dataclass(kw_only=True, slots=True)
class ApplicationFilters:
    """Filters for list_by_filters(). None means "no filter on this field".

    Exactly one of job_id / candidate_id is expected to be set by the
    use case that builds this — never both None, and the use case is
    responsible for choosing the right one based on who's asking
    (employer -> job_id, candidate -> candidate_id).
    """

    job_id: UUID | None = field(default=None)
    candidate_id: UUID | None = field(default=None)
    status: ApplicationStatus | None = field(default=None)


@dataclass(kw_only=True, slots=True)
class ApplicationView:
    """Presentation-ready application: the domain entity plus a freshly
    generated presigned CV URL. Never persisted — assembled per-request
    in the use case, since presigned URLs expire (TTL 1h per spec) and
    must never be cached or stored in the DB."""

    application: Application
    cv_download_url: str
