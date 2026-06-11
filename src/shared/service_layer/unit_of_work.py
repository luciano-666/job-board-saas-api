from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from types import TracebackType

from src.users.domain.events import DomainEvent


class IntegrityConflict(RuntimeError):
    """Raised when persistence rejects a conflicting write."""


class AbstractUnitOfWork(ABC):
    """Provide atomic persistence and event collection."""

    async def __aenter__(self) -> AbstractUnitOfWork:
        """Enter the transaction boundary."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Roll back work that did not explicitly commit."""
        await self.rollback()

    @property
    @abstractmethod
    def repositories(self) -> list:
        """
        Return repositories participating in the current transaction.
        """
        raise NotImplementedError

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        """Roll back the current transaction."""
        raise NotImplementedError

    def collect_new_events(self) -> Iterator[DomainEvent]:
        """Yield pending events from aggregates seen in this transaction."""
        for repo in self.repositories:
            for entity in repo.seen:
                while entity.events:
                    yield entity.events.pop(0)
