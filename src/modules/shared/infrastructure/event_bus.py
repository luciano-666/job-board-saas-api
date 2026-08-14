import structlog
from collections import defaultdict

from src.modules.shared.application.interfaces import EventHandler
from src.modules.shared.domain.events import DomainEvent

logger = structlog.get_logger(__name__)


class InMemoryEventBus:
    """Synchronous in-process pub/sub. No persistence, no retries —
    handlers run in the same request lifecycle right after commit.
    Sufficient for current scale; upgrade to outbox pattern only if
    at-least-once delivery across process restarts becomes a requirement.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            logger.debug(f"No handlers registered for {type(event).__name__}.")
            return

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                # A failing handler must never break the request/response
                # cycle — the DB commit already succeeded. Log and continue.
                logger.error(
                    f"Event handler failed for {type(event).__name__}.",
                    exc_info=e,
                )
