from typing import Protocol, Callable, Awaitable
from uuid import UUID

from src.modules.user.domain.entities import User
from src.modules.jobs.domain.entities import Job
from src.modules.shared.domain.events import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class ISharedUseCases(Protocol):
    async def get_user_by_id(self, id: UUID) -> User | None: ...

    async def get_user_by_email(self, email: str) -> User: ...

    async def update_user_password(self, user: User) -> None: ...

    async def get_job_by_id(self, id: UUID) -> Job | None: ...


class IEventBus(Protocol):
    def subscribe(
        self, event_type: type[DomainEvent], handler: EventHandler
    ) -> None: ...

    async def publish(self, event: DomainEvent) -> None: ...


class IUnitOfWork(Protocol):
    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    def track(self, entity: "object") -> None:
        """Register an entity whose pending domain events must be
        collected and dispatched after a successful commit."""
        ...
