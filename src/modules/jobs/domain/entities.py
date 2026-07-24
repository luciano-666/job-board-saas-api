from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import UUID, uuid4

from src.modules.shared.domain.entities import DomainError
from src.modules.jobs.application.enums import JobStatus, JobType
from src.modules.jobs.domain.value_objects import SalaryRange


@dataclass(kw_only=True, slots=True)
class Job:
    title: str
    description: str
    location: str
    salary: SalaryRange
    job_type: JobType
    skills: list[str]
    employer_id: UUID

    # Application-managed fields
    id: UUID = field(default_factory=uuid4)
    status: JobStatus = field(default=JobStatus.DRAFT)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self._normalize()
        self._validate()

    def _normalize(self) -> None:
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.location = self.location.strip()
        # Deduplicate while preserving first-seen order.
        normalized_skills: list[str] = []
        for skill in self.skills:
            normalized = skill.strip().lower()
            if normalized and normalized not in normalized_skills:
                normalized_skills.append(normalized)
        self.skills = normalized_skills

    def _validate(self) -> None:
        if not self.title:
            raise DomainError("Job title is required.")

        if not self.description:
            raise DomainError("Job description is required.")

        if not self.location:
            raise DomainError("Job location is required.")

        if not self.skills:
            raise DomainError("Job must have at least one skill.")

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def publish(self) -> None:
        if self.status != JobStatus.DRAFT:
            raise DomainError("Only a draft job can be published.")
        self.status = JobStatus.OPEN
        self._touch()

    def close(self) -> None:
        if self.status != JobStatus.OPEN:
            raise DomainError("Only an open job can be closed.")
        self.status = JobStatus.CLOSED
        self._touch()

    def archive(self) -> None:
        if self.status != JobStatus.CLOSED:
            raise DomainError("Only a closed job can be archived.")
        self.status = JobStatus.ARCHIVED
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.now(UTC)
