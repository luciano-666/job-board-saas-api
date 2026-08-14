from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Base class for all domain events. Immutable — represents a fact
    that already happened, never mutated after creation."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class HasDomainEvents:
    """Mixin for entities that need to record domain events during their
    lifecycle (e.g. Job.publish() records JobPublishedEvent).

    Entities call self._record_event(...) inside their behavior methods.
    The UnitOfWork pulls events via pull_domain_events() after a
    successful repository call, right before dispatching.
    """

    def __post_init_events__(self) -> None:
        # Called explicitly from entity __post_init__ since dataclasses
        # with slots don't reliably support mixin default fields.
        object.__setattr__(self, "_domain_events", [])

    def _record_event(self, event: DomainEvent) -> None:
        if not hasattr(self, "_domain_events"):
            self.__post_init_events__()
        self._domain_events.append(event)  # type: ignore[attr-defined]

    def pull_domain_events(self) -> list[DomainEvent]:
        events = getattr(self, "_domain_events", [])
        if hasattr(self, "_domain_events"):
            self._domain_events = []  # type: ignore[attr-defined]
        return events
