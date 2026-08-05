from typing import Optional
from uuid import UUID

from sqlalchemy import (
    String,
    Text,
    Integer,
    Enum as SQLEnum,
    ForeignKey,
    Computed,
    Index,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from src.core.config import settings
from src.modules.jobs.application.enums import JobStatus, JobType
from src.modules.jobs.domain.entities import Job
from src.modules.jobs.domain.value_objects import SalaryRange
from src.modules.shared.infrastructure.models import BaseModel


class JobModel(BaseModel):
    __tablename__ = f"{settings.APPLICATION_TABLE_PREFIX}_jobs"
    __table_args__ = (
        Index(
            "ix_jobs_search_vector_gin",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    title: Mapped[str] = mapped_column(
        String(200),
        name="title",
        comment="Job posting title",
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        name="description",
        comment="Full job description",
        nullable=False,
    )

    location: Mapped[str] = mapped_column(
        String(255),
        name="location",
        comment="Job location",
        nullable=False,
    )

    salary_min: Mapped[Optional[int]] = mapped_column(
        Integer,
        name="salary_min",
        comment="Minimum salary in the range (nullable — either bound optional)",
        nullable=True,
        default=None,
    )

    salary_max: Mapped[Optional[int]] = mapped_column(
        Integer,
        name="salary_max",
        comment="Maximum salary in the range (nullable — either bound optional)",
        nullable=True,
        default=None,
    )

    job_type: Mapped[JobType] = mapped_column(
        SQLEnum(JobType, name="job_type_enum"),
        name="job_type",
        comment="Employment type of the job",
        nullable=False,
    )

    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="job_status_enum"),
        name="status",
        comment="Lifecycle status of the job posting",
        nullable=False,
        default=JobStatus.DRAFT,
    )

    skills: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        name="skills",
        comment="Required skills for the job",
        nullable=False,
        default=list,
    )

    employer_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{settings.APPLICATION_TABLE_PREFIX}_users.id", ondelete="CASCADE"),
        name="employer_id",
        comment="Identifier of the employer who owns this job",
        nullable=False,
    )

    # Generated column (Postgres STORED), populated automatically by the DB
    # on every INSERT/UPDATE. The GIN index over this column is created in
    # the Alembic migration, never at runtime — see constraint #5 in the spec.
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(description, '')), 'B')",
            persisted=True,
        ),
        name="search_vector",
        comment="Full-text search vector, auto-derived from title + description",
        nullable=True,
    )

    @classmethod
    def from_entity(cls, job: Job) -> "JobModel":
        return cls(
            id=job.id,
            title=job.title,
            description=job.description,
            location=job.location,
            salary_min=job.salary.min,
            salary_max=job.salary.max,
            job_type=job.job_type,
            status=job.status,
            skills=job.skills,
            employer_id=job.employer_id,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def to_entity(self) -> Job:
        return Job(
            id=self.id,
            title=self.title,
            description=self.description,
            location=self.location,
            salary=SalaryRange(min=self.salary_min, max=self.salary_max),
            job_type=self.job_type,
            status=self.status,
            skills=list(self.skills),
            employer_id=self.employer_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
