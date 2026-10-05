from __future__ import annotations
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.modules.applications.application.enums import ApplicationStatus
from src.modules.applications.application.dto import ApplicationView
from src.modules.shared.application.enums import ResponseMessages


class ApplicationResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    job_id: UUID
    status: ApplicationStatus
    cv_download_url: str = Field(
        description="Presigned URL to download the CV, valid for a limited time (1h)."
    )

    model_config = ConfigDict(title="ApplicationResponse", extra="forbid")

    @classmethod
    def from_view(cls, view: ApplicationView) -> "ApplicationResponse":
        return cls(
            id=view.application.id,
            candidate_id=view.application.candidate_id,
            job_id=view.application.job_id,
            status=view.application.status,
            cv_download_url=view.cv_download_url,
        )


class ApplicationListQuery(BaseModel):
    cursor: Optional[str] = Field(default=None)
    limit: int = Field(default=20, ge=1, le=100)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ApplicationListResponse(BaseModel):
    message: str = ResponseMessages.RETRIEVED.value
    data: list[ApplicationResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False

    model_config = ConfigDict(title="ApplicationListResponse", extra="forbid")
