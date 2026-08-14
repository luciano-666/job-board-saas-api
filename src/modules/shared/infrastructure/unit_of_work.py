import structlog
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.event_bus import event_bus

logger = structlog.get_logger(__name__)


class SqlAlchemyUnitOfWork:
    """Wraps the request-scoped AsyncSession. Does NOT own session
    lifecycle (get_async_session still owns open/close) — it only adds
    an explicit commit boundary that use cases call intentionally,
    and collects domain events from tracked entities to dispatch
    strictly after that commit succeeds.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._tracked_entities: list[Any] = []

    def track(self, entity: Any) -> None:
        self._tracked_entities.append(entity)

    async def commit(self) -> None:
        try:
            await self.session.commit()
        except Exception as e:
            logger.error("Commit failed in unit of work.", exc_info=e)
            await self.session.rollback()
            raise

        # Only reachable if commit succeeded — safe to dispatch now.
        for entity in self._tracked_entities:
            pull = getattr(entity, "pull_domain_events", None)
            if pull is None:
                continue
            for domain_event in pull():
                await event_bus.publish(domain_event)

        self._tracked_entities.clear()

    async def rollback(self) -> None:
        await self.session.rollback()
        self._tracked_entities.clear()
