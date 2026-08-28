from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import UUID, uuid4

from src.modules.shared.domain.entities import DomainError
from src.modules.applications.application.enums import ApplicationStatus


@dataclass(kw_only=True, slots=True)
class Application:
    candidate_id: UUID
    job_id: UUID
    cv_url: str

    # Application-managed fields
    id: UUID = field(default_factory=uuid4)
    status: ApplicationStatus = field(default=ApplicationStatus.SUBMITTED)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self._normalize()
        self._validate()

    def _normalize(self) -> None:
        self.cv_url = self.cv_url.strip()

    def _validate(self) -> None:
        if not self.cv_url:
            raise DomainError("Application cv_url is required.")

    def _touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    # ------------------------------------------------------------------
    # Status transitions
    #   submitted -> reviewing
    #   reviewing -> accepted
    #   reviewing -> rejected
    # ------------------------------------------------------------------

    def move_to_reviewing(self) -> None:
        if self.status != ApplicationStatus.SUBMITTED:
            raise DomainError("Only a submitted application can move to reviewing.")
        self.status = ApplicationStatus.REVIEWING
        self._touch()

    def accept(self) -> None:
        if self.status != ApplicationStatus.REVIEWING:
            raise DomainError("Only an application under reviewing can be accepted.")
        self.status = ApplicationStatus.ACCEPTED
        self._touch()

    def reject(self) -> None:
        if self.status != ApplicationStatus.REVIEWING:
            raise DomainError("Only an application under reviewing can be rejected.")
        self.status = ApplicationStatus.REJECTED
        self._touch()
