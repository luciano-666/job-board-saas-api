# src/modules/jobs/domain/events.py
from uuid import UUID
from src.modules.shared.domain.events import DomainEvent


class JobPublishedEvent(DomainEvent):
    job_id: UUID
    employer_id: UUID
