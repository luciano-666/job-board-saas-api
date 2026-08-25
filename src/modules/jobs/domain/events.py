from dataclasses import dataclass
from uuid import UUID
from src.modules.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class JobPublishedEvent(DomainEvent):
    job_id: UUID
    employer_id: UUID
