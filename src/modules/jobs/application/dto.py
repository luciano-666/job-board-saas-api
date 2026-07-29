"""Application-layer DTOs for the jobs module: filters, cursor pagination."""

from __future__ import annotations
from dataclasses import dataclass, field

import base64
import binascii
import json
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from src.modules.jobs.application.enums import JobStatus, JobType

T = TypeVar("T")


@dataclass(frozen=True, slots=True, kw_only=True)
class JobCursor:
    """Opaque pagination cursor encoding (created_at, job_id).

    Sorting is by created_at DESC, job_id DESC as tiebreaker, so the
    cursor carries both fields to resume a listing query deterministically
    without relying on OFFSET (per spec: no offset-based pagination).
    """

    created_at: datetime
    job_id: UUID

    def encode(self) -> str:
        payload = {
            "created_at": self.created_at.isoformat(),
            "job_id": str(self.job_id),
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    @classmethod
    def decode(cls, cursor: str) -> "JobCursor":
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
            payload = json.loads(raw)
        except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError("Invalid pagination cursor.") from e

        if (
            not isinstance(payload, dict)
            or "created_at" not in payload
            or "job_id" not in payload
        ):
            raise ValueError("Malformed pagination cursor payload.")

        try:
            return cls(
                created_at=datetime.fromisoformat(payload["created_at"]),
                job_id=UUID(payload["job_id"]),
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError("Malformed pagination cursor payload.") from e


@dataclass(kw_only=True, slots=True)
class JobFilters:
    """Filter parameters accepted by list_by_filters().

    All fields are optional — None means "no filter on this field".
    """

    location: str | None = field(default=None)
    job_type: JobType | None = field(default=None)
    salary_min: int | None = field(default=None)
    skills: list[str] | None = field(default=None)
    # NOTE: no dedicated Company bounded context exists yet — "company" in
    # the spec maps directly to the employer's User.id. Renamed at the API
    # boundary as "company" per spec wording, but internally this filters
    # by JobModel.employer_id.
    company_id: UUID | None = field(default=None)
    status: JobStatus | None = field(default=None)
    search: str | None = field(default=None)  # full-text search term (tsvector)


@dataclass(kw_only=True, slots=True)
class CursorPage(Generic[T]):
    """A single page of cursor-paginated results."""

    items: list[T]
    next_cursor: str | None = field(default=None)
    has_more: bool = field(default=False)
