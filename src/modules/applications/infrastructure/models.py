from uuid import UUID

from sqlalchemy import (
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.config import settings
from src.modules.applications.application.enums import ApplicationStatus
from src.modules.applications.domain.entities import Application
from src.modules.shared.infrastructure.models import BaseModel


class ApplicationModel(BaseModel):
    __tablename__ = f"{settings.APPLICATION_TABLE_PREFIX}_applications"
    __table_args__ = (
        # Two-layer defense (see APP-3): this constraint is the source of
        # truth for race-condition safety; the use-case level
        # exists_by_candidate_and_job() check is the fast, friendly 409.
        UniqueConstraint(
            "candidate_id", "job_id", name="uq_applications_candidate_id_job_id"
        ),
        Index("ix_applications_candidate_id_job_id", "candidate_id", "job_id"),
        Index("ix_applications_job_id_status", "job_id", "status"),
    )

    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{settings.APPLICATION_TABLE_PREFIX}_users.id", ondelete="CASCADE"),
        name="candidate_id",
        comment="Identifier of the candidate who submitted this application",
        nullable=False,
    )

    job_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{settings.APPLICATION_TABLE_PREFIX}_jobs.id", ondelete="CASCADE"),
        name="job_id",
        comment="Identifier of the job this application targets",
        nullable=False,
    )

    cv_url: Mapped[str] = mapped_column(
        String(2048),
        name="cv_url",
        comment="S3 URL (or presigned URL reference) of the uploaded CV",
        nullable=False,
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, name="application_status_enum"),
        name="status",
        comment="Lifecycle status of the application",
        nullable=False,
        default=ApplicationStatus.SUBMITTED,
    )

    @classmethod
    def from_entity(cls, application: Application) -> "ApplicationModel":
        return cls(
            id=application.id,
            candidate_id=application.candidate_id,
            job_id=application.job_id,
            cv_url=application.cv_url,
            status=application.status,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )

    def to_entity(self) -> Application:
        return Application(
            id=self.id,
            candidate_id=self.candidate_id,
            job_id=self.job_id,
            cv_url=self.cv_url,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
