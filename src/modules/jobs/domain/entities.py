from src.modules.jobs.domain.events import JobPublishedEvent
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4

from src.modules.shared.domain.entities import DomainError
from src.modules.jobs.application.enums import JobStatus, JobType
from src.modules.jobs.domain.value_objects import SalaryRange
from src.modules.shared.domain.events import DomainEvent


@dataclass(kw_only=True, slots=True)
class Job:
    title: str
    description: str
    location: str
    job_type: JobType
    skills: list[str]
    employer_id: UUID

    _domain_events: list[DomainEvent] = field(
        default_factory=list, repr=False, compare=False
    )

    # Optional — either bound may be omitted
    salary: SalaryRange = field(default_factory=lambda: SalaryRange())

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
        seen: list[str] = []
        for skill in self.skills:
            normalized = skill.strip().lower()
            if normalized and normalized not in seen:
                seen.append(normalized)
        self.skills = seen

    def _validate(self) -> None:
        if not self.title:
            raise DomainError("Job title is required.")

        if not self.description:
            raise DomainError("Job description is required.")

        if not self.location:
            raise DomainError("Job location is required.")

        if not self.skills:
            raise DomainError("Job must have at least one skill.")

    def pull_domain_events(self) -> list[DomainEvent]:
        events, self._domain_events = self._domain_events, []
        return events

    # ------------------------------------------------------------------
    # Status transitions
    #   draft  -> open      (publish)
    #   open   -> closed    (close)
    #   open   -> archived  (archive, only 90+ days after created_at)
    #   closed -> archived  (archive, only 90+ days after created_at)
    # ------------------------------------------------------------------

    ARCHIVE_ELIGIBLE_AFTER = timedelta(days=90)

    def publish(self) -> None:
        """Transition from draft to open."""
        if self.status != JobStatus.DRAFT:
            raise DomainError("Only a draft job can be published.")
        self.status = JobStatus.OPEN
        self._touch()
        self._domain_events.append(
            JobPublishedEvent(job_id=self.id, employer_id=self.employer_id)
        )

    def close(self) -> None:
        """Transition from open to closed."""
        if self.status != JobStatus.OPEN:
            raise DomainError("Only an open job can be closed.")
        self.status = JobStatus.CLOSED
        self._touch()

    def archive(self) -> None:
        """Transition from open or closed to archived.

        Only allowed once the job has existed for at least 90 days,
        counted from created_at — matches the scheduled auto-archive
        rule described in the project spec.
        """
        if self.status not in (JobStatus.OPEN, JobStatus.CLOSED):
            raise DomainError("Only an open or closed job can be archived.")

        if not self._is_eligible_for_archive():
            raise DomainError(
                "A job can only be archived after 90 days since its creation."
            )

        self.status = JobStatus.ARCHIVED
        self._touch()

    def _is_eligible_for_archive(self) -> bool:
        age = datetime.now(UTC) - self.created_at
        return age >= self.ARCHIVE_ELIGIBLE_AFTER

    def _touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    def update_details(
        self,
        *,
        title: str,
        description: str,
        location: str,
        job_type: JobType,
        skills: list[str],
        salary: SalaryRange,
    ) -> None:
        """Update editable job fields. Status transitions have dedicated methods."""
        self.title = title
        self.description = description
        self.location = location
        self.job_type = job_type
        self.skills = skills
        self.salary = salary
        self._normalize()
        self._validate()
        self._touch()
